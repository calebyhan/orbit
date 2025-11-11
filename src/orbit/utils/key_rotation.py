"""Multi-API-key rotation manager for rate-limited services.

Supports up to 5 API keys with round-robin or least-used rotation strategies.
Tracks daily usage per key and handles failover when keys are exhausted.

Used by Gemini LLM batching and other rate-limited services in ORBIT.
"""

import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class RotationStrategy(Enum):
    """Key rotation strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_USED = "least_used"


@dataclass
class KeyUsage:
    """Track usage statistics for a single API key."""
    key_name: str
    key_value: str
    requests_today: int = 0
    tokens_today: int = 0
    last_used_at: Optional[datetime] = None
    last_reset_date: Optional[str] = None

    def reset_if_new_day(self, timezone_name: str = "US/Pacific"):
        """Reset daily counters if it's a new day.

        Args:
            timezone_name: Timezone for daily reset (Gemini resets at midnight Pacific)
        """
        import pytz
        tz = pytz.timezone(timezone_name)
        now_local = datetime.now(tz)
        today_str = now_local.date().isoformat()

        if self.last_reset_date != today_str:
            self.requests_today = 0
            self.tokens_today = 0
            self.last_reset_date = today_str


class KeyRotationManager:
    """Manage multiple API keys with rotation and quota tracking.

    Supports up to 5 keys with configurable rotation strategy and per-key quotas.
    Tracks daily usage and handles automatic failover when keys are exhausted.

    Example:
        >>> manager = KeyRotationManager(
        ...     env_prefix="GEMINI_API_KEY",
        ...     max_keys=5,
        ...     strategy=RotationStrategy.ROUND_ROBIN,
        ...     quota_rpd=200,  # 200 requests per day per key
        ... )
        >>> key = manager.get_next_key()
        >>> manager.record_usage(key_name=key.key_name, requests=1, tokens=1500)
    """

    def __init__(
        self,
        env_prefix: str,
        max_keys: int = 5,
        strategy: RotationStrategy = RotationStrategy.ROUND_ROBIN,
        quota_rpd: Optional[int] = None,
        quota_rpm: Optional[int] = None,
        quota_tpm: Optional[int] = None,
        reset_timezone: str = "US/Pacific",
        safety_margin: float = 0.95,  # Use up to 95% of quota before failover
    ):
        """Initialize key rotation manager.

        Args:
            env_prefix: Environment variable prefix (e.g., "GEMINI_API_KEY")
            max_keys: Maximum number of keys to load (1-5)
            strategy: Rotation strategy (ROUND_ROBIN or LEAST_USED)
            quota_rpd: Requests per day per key (optional)
            quota_rpm: Requests per minute per key (optional)
            quota_tpm: Tokens per minute per key (optional)
            reset_timezone: Timezone for daily reset (e.g., "US/Pacific")
            safety_margin: Use up to this fraction of quota before failover (0.0-1.0)
        """
        self.env_prefix = env_prefix
        self.max_keys = max_keys
        self.strategy = strategy
        self.quota_rpd = quota_rpd
        self.quota_rpm = quota_rpm
        self.quota_tpm = quota_tpm
        self.reset_timezone = reset_timezone
        self.safety_margin = safety_margin

        # Load keys from environment
        self.keys: list[KeyUsage] = []
        self._load_keys()

        # Rotation state
        self.current_index = 0

        # Statistics
        self.total_requests = 0
        self.total_tokens = 0
        self.key_switches = 0

    def _load_keys(self):
        """Load API keys from environment variables.

        Looks for keys named: {env_prefix}_1, {env_prefix}_2, ..., {env_prefix}_{max_keys}
        """
        for i in range(1, self.max_keys + 1):
            key_name = f"{self.env_prefix}_{i}"
            key_value = os.getenv(key_name)

            if key_value and key_value.strip():
                self.keys.append(KeyUsage(
                    key_name=key_name,
                    key_value=key_value.strip(),
                ))

        if not self.keys:
            raise ValueError(
                f"No API keys found for prefix '{self.env_prefix}'. "
                f"Set {self.env_prefix}_1, {self.env_prefix}_2, etc. in .env"
            )

        print(f"✓ Loaded {len(self.keys)} API key(s) for {self.env_prefix}")

    def _reset_all_keys_if_new_day(self):
        """Reset all keys if it's a new day."""
        for key in self.keys:
            key.reset_if_new_day(self.reset_timezone)

    def _is_key_available(self, key: KeyUsage) -> bool:
        """Check if key has available quota.

        Args:
            key: Key to check

        Returns:
            True if key is available, False if exhausted
        """
        # Reset if new day
        key.reset_if_new_day(self.reset_timezone)

        # Check daily quota
        if self.quota_rpd:
            quota_limit = int(self.quota_rpd * self.safety_margin)
            if key.requests_today >= quota_limit:
                return False

        # Other quotas (RPM, TPM) would require time-window tracking
        # For now, we only track daily quotas (RPD)

        return True

    def get_next_key(self) -> KeyUsage:
        """Get next available API key according to rotation strategy.

        Returns:
            KeyUsage object with key details

        Raises:
            RuntimeError: If all keys are exhausted
        """
        self._reset_all_keys_if_new_day()

        if self.strategy == RotationStrategy.ROUND_ROBIN:
            return self._get_next_round_robin()
        elif self.strategy == RotationStrategy.LEAST_USED:
            return self._get_least_used()
        else:
            raise ValueError(f"Unknown rotation strategy: {self.strategy}")

    def _get_next_round_robin(self) -> KeyUsage:
        """Get next key using round-robin strategy.

        Returns:
            KeyUsage object

        Raises:
            RuntimeError: If all keys are exhausted
        """
        # Try all keys starting from current index
        for _ in range(len(self.keys)):
            key = self.keys[self.current_index]

            # Move to next key for next call
            next_index = (self.current_index + 1) % len(self.keys)
            if next_index != self.current_index:
                self.key_switches += 1
            self.current_index = next_index

            if self._is_key_available(key):
                return key

        # All keys exhausted
        raise RuntimeError(
            f"All {len(self.keys)} API keys exhausted. "
            f"Daily quota: {self.quota_rpd} RPD per key. "
            f"Try again after midnight {self.reset_timezone}."
        )

    def _get_least_used(self) -> KeyUsage:
        """Get least-used key.

        Returns:
            KeyUsage object with lowest usage

        Raises:
            RuntimeError: If all keys are exhausted
        """
        # Find available key with lowest usage
        available_keys = [k for k in self.keys if self._is_key_available(k)]

        if not available_keys:
            raise RuntimeError(
                f"All {len(self.keys)} API keys exhausted. "
                f"Daily quota: {self.quota_rpd} RPD per key. "
                f"Try again after midnight {self.reset_timezone}."
            )

        # Sort by requests_today (ascending)
        key = min(available_keys, key=lambda k: k.requests_today)
        self.key_switches += 1
        return key

    def record_usage(
        self,
        key_name: str,
        requests: int = 1,
        tokens: int = 0,
    ):
        """Record API usage for a key.

        Args:
            key_name: Key name (e.g., "GEMINI_API_KEY_1")
            requests: Number of requests made
            tokens: Number of tokens used
        """
        # Find key
        for key in self.keys:
            if key.key_name == key_name:
                key.requests_today += requests
                key.tokens_today += tokens
                key.last_used_at = datetime.now(timezone.utc)
                break

        # Update totals
        self.total_requests += requests
        self.total_tokens += tokens

    def get_stats(self) -> dict:
        """Get usage statistics for all keys.

        Returns:
            Dict with statistics
        """
        self._reset_all_keys_if_new_day()

        key_stats = []
        for key in self.keys:
            key_stats.append({
                "key_name": key.key_name,
                "requests_today": key.requests_today,
                "tokens_today": key.tokens_today,
                "quota_rpd": self.quota_rpd,
                "usage_pct": (key.requests_today / self.quota_rpd * 100) if self.quota_rpd else 0,
                "available": self._is_key_available(key),
            })

        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "key_switches": self.key_switches,
            "num_keys": len(self.keys),
            "strategy": self.strategy.value,
            "keys": key_stats,
        }

    def log_stats(self):
        """Log current usage statistics."""
        stats = self.get_stats()

        print("\n" + "="*60)
        print("API Key Rotation Statistics:")
        print(f"  Strategy: {stats['strategy']}")
        print(f"  Total keys: {stats['num_keys']}")
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Total tokens: {stats['total_tokens']}")
        print(f"  Key switches: {stats['key_switches']}")
        print("\nPer-key usage:")
        for key_stat in stats["keys"]:
            status = "✓" if key_stat["available"] else "✗"
            print(f"  {status} {key_stat['key_name']}: {key_stat['requests_today']}/{key_stat['quota_rpd']} RPD ({key_stat['usage_pct']:.1f}%)")
        print("="*60)


if __name__ == "__main__":
    # Example usage / testing
    print("Testing KeyRotationManager...\n")

    # Test with mock environment
    os.environ["TEST_API_KEY_1"] = "key1_value"
    os.environ["TEST_API_KEY_2"] = "key2_value"
    os.environ["TEST_API_KEY_3"] = "key3_value"

    # Create manager
    manager = KeyRotationManager(
        env_prefix="TEST_API_KEY",
        max_keys=5,
        strategy=RotationStrategy.ROUND_ROBIN,
        quota_rpd=200,
    )

    # Simulate usage
    print("\nSimulating API usage...\n")
    for i in range(10):
        key = manager.get_next_key()
        print(f"Request {i+1}: Using {key.key_name}")
        manager.record_usage(key_name=key.key_name, requests=1, tokens=1500)

    # Show statistics
    manager.log_stats()
