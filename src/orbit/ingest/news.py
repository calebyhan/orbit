"""ORBIT News Ingestion - Alpaca News WebSocket client.

Connects to Alpaca's news WebSocket, streams real-time news for configured symbols,
normalizes messages, deduplicates, enforces point-in-time cutoff rules, and persists
to data/raw/news/ and data/curated/news/ (or ORBIT_DATA_DIR if configured).

Implements M1 deliverable: ingest:news
"""

import hashlib
import json
import os
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import websocket

from orbit import io as orbit_io


def get_alpaca_creds() -> tuple[str, str]:
    """Get Alpaca API credentials from environment.

    Returns:
        Tuple of (api_key, api_secret)

    Raises:
        ValueError: If credentials not found in environment
    """
    api_key = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_API_SECRET")

    if not api_key or not api_secret:
        raise ValueError(
            "Alpaca credentials not found. Set ALPACA_API_KEY and ALPACA_API_SECRET in .env"
        )

    return api_key, api_secret


def compute_msg_id(msg: dict) -> str:
    """Compute unique message ID from Alpaca news message.

    Primary: Use provider's 'id' field if present
    Fallback: SHA-1 hash of (headline + source + published_at)

    Args:
        msg: Normalized news message dict

    Returns:
        Unique message ID string
    """
    # Try provider ID first
    if "id" in msg and msg["id"]:
        return str(msg["id"])

    # Fallback to content hash
    content = f"{msg.get('headline', '')}{msg.get('source', '')}{msg.get('published_at', '')}"
    return hashlib.sha1(content.encode()).hexdigest()


def normalize_alpaca_message(msg: dict, received_at: datetime, run_id: str) -> dict:
    """Normalize Alpaca news message to canonical schema.

    Args:
        msg: Raw message from Alpaca WebSocket
        received_at: When our client received the message (UTC)
        run_id: Unique run identifier

    Returns:
        Normalized message dict matching schema
    """
    # Extract core fields
    normalized = {
        "msg_id": compute_msg_id(msg),
        "published_at": pd.to_datetime(msg.get("created_at") or msg.get("updated_at")),
        "received_at": pd.to_datetime(received_at),
        "symbols": msg.get("symbols", []),
        "headline": msg.get("headline", ""),
        "summary": msg.get("summary"),
        "source": msg.get("source", ""),
        "url": msg.get("url"),
        "raw": json.dumps(msg),  # Store original for audit
        "run_id": run_id,
    }

    return normalized


def validate_news_message(msg: dict) -> list[str]:
    """Validate a normalized news message.

    Args:
        msg: Normalized message dict

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Required fields
    if not msg.get("headline"):
        errors.append("Missing headline")

    if not msg.get("published_at"):
        errors.append("Missing published_at")

    # Validate timestamp ordering (with tolerance for small clock skew)
    if msg.get("published_at") and msg.get("received_at"):
        pub_ts = pd.to_datetime(msg["published_at"])
        rec_ts = pd.to_datetime(msg["received_at"])

        # Allow small clock skew (30 seconds)
        if pub_ts > rec_ts + pd.Timedelta(seconds=30):
            errors.append(f"published_at ({pub_ts}) > received_at ({rec_ts})")

    # Validate published_at is not in future
    now = pd.Timestamp.utcnow()
    if msg.get("published_at"):
        pub_ts = pd.to_datetime(msg["published_at"])
        if pub_ts > now + pd.Timedelta(seconds=30):  # Allow small tolerance
            errors.append(f"published_at ({pub_ts}) is in the future")

    return errors


class NewsBuffer:
    """In-memory buffer for news messages with flush policy."""

    def __init__(self, flush_size: int = 100, flush_interval_sec: float = 300.0):
        """Initialize buffer.

        Args:
            flush_size: Flush when buffer reaches this size
            flush_interval_sec: Flush after this many seconds since last flush
        """
        self.buffer = deque()
        self.seen_ids = set()
        self.flush_size = flush_size
        self.flush_interval_sec = flush_interval_sec
        self.last_flush_time = time.time()

    def add(self, msg: dict) -> bool:
        """Add message to buffer if not duplicate.

        Args:
            msg: Normalized message dict

        Returns:
            True if added, False if duplicate
        """
        msg_id = msg["msg_id"]

        if msg_id in self.seen_ids:
            return False

        self.seen_ids.add(msg_id)
        self.buffer.append(msg)
        return True

    def should_flush(self) -> bool:
        """Check if buffer should be flushed.

        Returns:
            True if flush conditions met
        """
        if len(self.buffer) >= self.flush_size:
            return True

        if time.time() - self.last_flush_time >= self.flush_interval_sec:
            return True

        return False

    def get_and_clear(self) -> list[dict]:
        """Get all messages and clear buffer.

        Returns:
            List of buffered messages
        """
        messages = list(self.buffer)
        self.buffer.clear()
        self.last_flush_time = time.time()
        return messages


def flush_to_parquet(messages: list[dict], base_dir: str = "raw/news") -> Optional[Path]:
    """Flush buffered messages to Parquet file.

    Args:
        messages: List of normalized message dicts
        base_dir: Base directory for output (relative to ORBIT_DATA_DIR)

    Returns:
        Path to written file, or None if no messages
    """
    if not messages:
        return None

    # Convert to DataFrame
    df = pd.DataFrame(messages)

    # Partition by date (from published_at)
    df["date"] = pd.to_datetime(df["published_at"]).dt.date

    # Write partitioned by date
    # Use append mode to handle multiple flushes per day
    for date, group in df.groupby("date"):
        date_str = str(date)
        path = f"{base_dir}/date={date_str}/news.parquet"

        # Append to existing file if present
        orbit_io.write_parquet(group.drop(columns=["date"]), path, overwrite=False)

    return Path(base_dir)


class AlpacaNewsClient:
    """Alpaca News WebSocket client with reconnection and buffering."""

    def __init__(
        self,
        symbols: list[str],
        api_key: str,
        api_secret: str,
        stream_url: str = "wss://stream.data.alpaca.markets/v1beta1/news",
        flush_size: int = 100,
        flush_interval_sec: float = 300.0,
        max_reconnect_attempts: int = 5,
        backoff_base_ms: float = 500,
        backoff_max_ms: float = 10000,
        backoff_factor: float = 2.0,
        run_id: Optional[str] = None,
    ):
        """Initialize Alpaca news WebSocket client.

        Args:
            symbols: List of symbols to subscribe to (e.g., ["SPY", "VOO"])
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            stream_url: WebSocket URL
            flush_size: Buffer flush size
            flush_interval_sec: Buffer flush interval
            max_reconnect_attempts: Max reconnection attempts
            backoff_base_ms: Initial backoff delay (ms)
            backoff_max_ms: Max backoff delay (ms)
            backoff_factor: Backoff multiplier
            run_id: Unique run identifier (auto-generated if None)
        """
        self.symbols = symbols
        self.api_key = api_key
        self.api_secret = api_secret
        self.stream_url = stream_url
        self.max_reconnect_attempts = max_reconnect_attempts
        self.backoff_base_ms = backoff_base_ms
        self.backoff_max_ms = backoff_max_ms
        self.backoff_factor = backoff_factor

        # Generate run_id if not provided
        if run_id is None:
            run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.run_id = run_id

        # Initialize buffer
        self.buffer = NewsBuffer(flush_size=flush_size, flush_interval_sec=flush_interval_sec)

        # Connection state
        self.ws = None
        self.connected = False
        self.authenticated = False
        self.subscribed = False
        self.reconnect_attempt = 0

        # Statistics
        self.messages_received = 0
        self.messages_buffered = 0
        self.messages_rejected = 0
        self.flushes_completed = 0

    def _compute_backoff(self, attempt: int) -> float:
        """Compute exponential backoff delay with jitter.

        Args:
            attempt: Reconnection attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay_ms = min(self.backoff_max_ms, self.backoff_base_ms * (self.backoff_factor ** attempt))
        # Add jitter (0.5 to 1.5x)
        import random
        jitter = 0.5 + random.random()
        return (delay_ms * jitter) / 1000.0

    def _on_open(self, ws):
        """WebSocket on_open callback."""
        print(f"✓ WebSocket connected to {self.stream_url}")
        self.connected = True
        self.reconnect_attempt = 0

        # Send authentication
        auth_msg = {
            "action": "auth",
            "key": self.api_key,
            "secret": self.api_secret,
        }
        ws.send(json.dumps(auth_msg))
        print("  → Sent authentication")

    def _on_message(self, ws, message):
        """WebSocket on_message callback."""
        try:
            msg = json.loads(message)
            msg_type = msg.get("T")

            # Handle connection messages
            if msg_type == "success" and msg.get("msg") == "authenticated":
                print("✓ Authenticated successfully")
                self.authenticated = True

                # Subscribe to news for symbols
                subscribe_msg = {
                    "action": "subscribe",
                    "news": self.symbols,
                }
                ws.send(json.dumps(subscribe_msg))
                print(f"  → Subscribed to news for: {self.symbols}")
                return

            if msg_type == "subscription":
                print(f"✓ Subscription confirmed: {msg}")
                self.subscribed = True
                return

            # Handle news messages
            if msg_type == "n":  # News message
                self.messages_received += 1

                # Normalize message
                received_at = datetime.now(timezone.utc)
                normalized = normalize_alpaca_message(msg, received_at, self.run_id)

                # Validate
                errors = validate_news_message(normalized)
                if errors:
                    self.messages_rejected += 1
                    print(f"⚠ Validation failed for message: {errors}")
                    # Write to rejects
                    reject_path = f"rejects/news/date={datetime.now(timezone.utc).date()}/rejects.jsonl"
                    # TODO: Implement reject writing
                    return

                # Add to buffer (dedupe happens here)
                if self.buffer.add(normalized):
                    self.messages_buffered += 1

                    # Print progress every 10 messages
                    if self.messages_buffered % 10 == 0:
                        print(f"  Buffered {self.messages_buffered} messages ({len(self.buffer.buffer)} in buffer)")

                # Check if buffer should flush
                if self.buffer.should_flush():
                    self._flush_buffer()

        except Exception as e:
            print(f"✗ Error processing message: {e}")

    def _on_error(self, ws, error):
        """WebSocket on_error callback."""
        print(f"✗ WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket on_close callback."""
        print(f"⚠ WebSocket closed (code: {close_status_code}, msg: {close_msg})")
        self.connected = False
        self.authenticated = False
        self.subscribed = False

        # Flush remaining buffer on close
        self._flush_buffer()

    def _flush_buffer(self):
        """Flush buffer to disk."""
        messages = self.buffer.get_and_clear()
        if messages:
            print(f"  → Flushing {len(messages)} messages to disk...")
            flush_to_parquet(messages, base_dir="raw/news")
            self.flushes_completed += 1
            print(f"  ✓ Flush complete (total flushes: {self.flushes_completed})")

    def connect(self):
        """Establish WebSocket connection with reconnection logic."""
        while self.reconnect_attempt < self.max_reconnect_attempts:
            try:
                print(f"\nConnecting to Alpaca News WebSocket (attempt {self.reconnect_attempt + 1}/{self.max_reconnect_attempts})...")

                # Create WebSocket connection
                self.ws = websocket.WebSocketApp(
                    self.stream_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )

                # Set User-Agent for compliance
                user_agent = os.getenv("ORBIT_USER_AGENT", "ORBIT/1.0 (Educational project; +https://github.com/calebyhan/orbit)")

                # Run WebSocket (blocking)
                self.ws.run_forever(
                    ping_interval=30,
                    ping_timeout=10,
                )

                # If we get here, connection closed
                if self.reconnect_attempt < self.max_reconnect_attempts - 1:
                    # Compute backoff delay
                    delay = self._compute_backoff(self.reconnect_attempt)
                    print(f"  Reconnecting in {delay:.1f}s...")
                    time.sleep(delay)
                    self.reconnect_attempt += 1
                else:
                    print(f"✗ Max reconnection attempts reached ({self.max_reconnect_attempts})")
                    break

            except KeyboardInterrupt:
                print("\n⚠ Interrupted by user")
                self._flush_buffer()
                break
            except Exception as e:
                print(f"✗ Connection error: {e}")
                if self.reconnect_attempt < self.max_reconnect_attempts - 1:
                    delay = self._compute_backoff(self.reconnect_attempt)
                    print(f"  Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    self.reconnect_attempt += 1
                else:
                    break

    def close(self):
        """Close connection and flush buffer."""
        print("\nClosing connection...")
        if self.ws:
            self.ws.close()
        self._flush_buffer()

        # Print statistics
        print("\n" + "="*60)
        print("News ingestion statistics:")
        print(f"  Messages received: {self.messages_received}")
        print(f"  Messages buffered: {self.messages_buffered}")
        print(f"  Messages rejected: {self.messages_rejected}")
        print(f"  Flushes completed: {self.flushes_completed}")
        print("="*60)


def ingest_news(
    symbols: Optional[list[str]] = None,
    stream_url: str = "wss://stream.data.alpaca.markets/v1beta1/news",
    flush_size: int = 100,
    flush_interval_sec: float = 300.0,
    max_reconnect_attempts: int = 5,
    run_id: Optional[str] = None,
) -> dict[str, Any]:
    """Ingest news from Alpaca WebSocket.

    This is the main entrypoint for news ingestion (M1 deliverable).
    Connects to Alpaca's news WebSocket, streams real-time news, and persists
    to data/raw/news/ (or ORBIT_DATA_DIR/raw/news/).

    Args:
        symbols: List of symbols to subscribe to (defaults to ["SPY", "VOO"])
        stream_url: Alpaca WebSocket URL
        flush_size: Buffer flush size
        flush_interval_sec: Buffer flush interval (seconds)
        max_reconnect_attempts: Max reconnection attempts
        run_id: Unique run identifier (auto-generated if None)

    Returns:
        Dict with statistics (messages_received, messages_buffered, etc.)

    Note:
        Data is written to ORBIT_DATA_DIR/raw/news/.
        Set ALPACA_API_KEY and ALPACA_API_SECRET in .env before running.
        This is a long-running process - press Ctrl+C to stop gracefully.
    """
    # Default symbols
    if symbols is None:
        symbols = ["SPY", "VOO"]

    # Get credentials
    api_key, api_secret = get_alpaca_creds()

    # Show data directory
    data_dir = orbit_io.get_data_dir()
    print(f"Data directory: {data_dir}")

    # Create client
    client = AlpacaNewsClient(
        symbols=symbols,
        api_key=api_key,
        api_secret=api_secret,
        stream_url=stream_url,
        flush_size=flush_size,
        flush_interval_sec=flush_interval_sec,
        max_reconnect_attempts=max_reconnect_attempts,
        run_id=run_id,
    )

    print(f"\nStarting news ingestion (run_id: {client.run_id})")
    print(f"Symbols: {symbols}")
    print(f"Press Ctrl+C to stop gracefully\n")

    try:
        # Connect (blocking)
        client.connect()
    finally:
        # Ensure cleanup
        client.close()

    # Return statistics
    return {
        "run_id": client.run_id,
        "messages_received": client.messages_received,
        "messages_buffered": client.messages_buffered,
        "messages_rejected": client.messages_rejected,
        "flushes_completed": client.flushes_completed,
    }


if __name__ == "__main__":
    # CLI entrypoint for testing
    import sys

    symbols = sys.argv[1:] if len(sys.argv) > 1 else None
    result = ingest_news(symbols=symbols)

    print("\nFinal statistics:")
    for key, value in result.items():
        print(f"  {key}: {value}")
