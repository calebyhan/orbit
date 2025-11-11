"""ORBIT LLM Batching - Gemini Sentiment Analysis.

Batch scores all news and social items using Gemini 2.5 Flash-Lite with multi-key rotation.
Implements structured sentiment output: sent_llm, stance, sarcasm, certainty, toxicity.

Implements M1 deliverable: llm_batching_gemini
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import requests

from orbit import io as orbit_io
from orbit.utils.key_rotation import KeyRotationManager, RotationStrategy


# Gemini API configuration
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-2.5-flash-lite"


def build_sentiment_prompt(items: list[dict]) -> dict:
    """Build Gemini prompt for batch sentiment analysis.

    Args:
        items: List of text items with fields: id, text, timestamp_utc, context

    Returns:
        Gemini API request payload
    """
    # System instruction
    system_instruction = """You are a financial sentiment annotator. For each JSON line, read `text` (+ optional `context`). Output **one JSON object per line** with **only** the fields in the response schema. No prose, no extra keys.

Response schema per item:
{
  "id": "item_id",
  "sent_llm": 0.62,             // float in [-1, 1]
  "stance": "bull",             // one of ["bull", "bear", "neutral"]
  "sarcasm": false,             // boolean
  "certainty": 0.76,            // [0,1]
  "toxicity": 0.03              // optional, [0,1]
}
"""

    # Build user message with JSONL items
    jsonl_lines = [json.dumps(item) for item in items]
    user_message = "\n".join(jsonl_lines)

    # Gemini request payload
    payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_message}]
            }
        ],
        "generationConfig": {
            "temperature": 0.0,  # Deterministic for consistency
            "response_mime_type": "application/json",  # Force JSON output
        }
    }

    return payload


def parse_gemini_response(response_text: str, input_items: list[dict]) -> list[dict]:
    """Parse Gemini response and validate 1:1 mapping with input.

    Args:
        response_text: Raw response text from Gemini
        input_items: Original input items for validation

    Returns:
        List of parsed sentiment results

    Raises:
        ValueError: If response doesn't match input or is invalid
    """
    try:
        # Try parsing as JSON array first
        results = json.loads(response_text)

        # If single object, wrap in list
        if isinstance(results, dict):
            results = [results]

        # Validate 1:1 mapping by ID
        input_ids = {item["id"] for item in input_items}
        result_ids = {r.get("id") for r in results}

        if input_ids != result_ids:
            missing = input_ids - result_ids
            extra = result_ids - input_ids
            raise ValueError(f"ID mismatch: missing={missing}, extra={extra}")

        # Validate and clamp values
        for result in results:
            # Clamp sent_llm to [-1, 1]
            if "sent_llm" in result:
                result["sent_llm"] = max(-1.0, min(1.0, float(result["sent_llm"])))

            # Clamp certainty to [0, 1]
            if "certainty" in result:
                result["certainty"] = max(0.0, min(1.0, float(result["certainty"])))

            # Clamp toxicity to [0, 1]
            if "toxicity" in result:
                result["toxicity"] = max(0.0, min(1.0, float(result["toxicity"])))

            # Validate stance
            if "stance" in result:
                if result["stance"] not in ["bull", "bear", "neutral"]:
                    result["stance"] = "neutral"  # Default to neutral if invalid

        return results

    except Exception as e:
        raise ValueError(f"Failed to parse Gemini response: {e}\nResponse: {response_text[:500]}")


def call_gemini_api(
    items: list[dict],
    api_key: str,
    model: str = DEFAULT_MODEL,
    timeout: int = 60,
    max_retries: int = 3,
) -> dict:
    """Call Gemini API for batch sentiment analysis.

    Args:
        items: List of text items to score
        api_key: Gemini API key
        model: Model name (default: gemini-2.5-flash-lite)
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts

    Returns:
        Dict with 'results' (list of sentiment scores) and 'raw_response' (full API response)

    Raises:
        requests.HTTPError: If all retries fail
    """
    # Build prompt
    payload = build_sentiment_prompt(items)

    # API endpoint
    url = f"{GEMINI_API_BASE}/models/{model}:generateContent?key={api_key}"

    # Retry loop with exponential backoff
    for attempt in range(max_retries):
        try:
            response = requests.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": os.getenv("ORBIT_USER_AGENT", "ORBIT/1.0"),
                },
                timeout=timeout,
            )

            # Check for rate limit
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"  ⚠ Rate limit hit, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    response.raise_for_status()

            response.raise_for_status()

            # Parse response
            response_data = response.json()

            # Extract text from response
            if "candidates" in response_data and len(response_data["candidates"]) > 0:
                candidate = response_data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    text = candidate["content"]["parts"][0].get("text", "")

                    # Parse sentiment results
                    results = parse_gemini_response(text, items)

                    return {
                        "results": results,
                        "raw_response": response_data,
                    }

            raise ValueError("No valid response from Gemini API")

        except requests.HTTPError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"  ⚠ HTTP error {e}, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise

    raise RuntimeError("Max retries exceeded")


def batch_score_gemini(
    items: pd.DataFrame,
    text_column: str = "text",
    id_column: str = "id",
    batch_size: int = 200,
    model: str = DEFAULT_MODEL,
    strategy: str = "round_robin",
    quota_rpd: int = 1000,
    run_id: Optional[str] = None,
    write_raw: bool = True,
) -> pd.DataFrame:
    """Batch score text items using Gemini with multi-key rotation.

    This is the main entrypoint for LLM batching (M1 deliverable).
    Processes all items through Gemini API with automatic key rotation and quota tracking.

    Args:
        items: DataFrame with text items to score
        text_column: Name of text column
        id_column: Name of ID column
        batch_size: Batch size (default: 200)
        model: Gemini model name (default: gemini-2.5-flash-lite)
        strategy: Key rotation strategy ("round_robin" or "least_used")
        quota_rpd: Requests per day per key (default: 1000 for gemini-2.5-flash-lite)
        run_id: Unique run identifier (auto-generated if None)
        write_raw: Whether to write raw req/resp to disk

    Returns:
        DataFrame with original columns plus sentiment fields:
        - sent_llm: Sentiment score in [-1, 1]
        - stance: One of ["bull", "bear", "neutral"]
        - sarcasm: Boolean
        - certainty: Score in [0, 1]
        - toxicity: Score in [0, 1] (optional)

    Note:
        Requires GEMINI_API_KEY_1 (and optionally _2, _3, _4, _5) in .env
        Raw requests/responses written to ORBIT_DATA_DIR/raw/gemini/
    """
    # Generate run_id if not provided
    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    print(f"\nStarting Gemini batch scoring (run_id: {run_id})")
    print(f"Items: {len(items)}")
    print(f"Batch size: {batch_size}")
    print(f"Model: {model}")

    # Initialize key rotation manager
    rotation_strategy = RotationStrategy.ROUND_ROBIN if strategy == "round_robin" else RotationStrategy.LEAST_USED

    key_manager = KeyRotationManager(
        env_prefix="GEMINI_API_KEY",
        max_keys=5,
        strategy=rotation_strategy,
        quota_rpd=quota_rpd,
    )

    # Process in batches
    results = []
    raw_records = []

    total_batches = (len(items) + batch_size - 1) // batch_size

    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min((batch_idx + 1) * batch_size, len(items))
        batch_items = items.iloc[start_idx:end_idx]

        print(f"\nProcessing batch {batch_idx + 1}/{total_batches} ({len(batch_items)} items)...")

        # Prepare batch input
        batch_input = []
        for _, row in batch_items.iterrows():
            batch_input.append({
                "id": str(row[id_column]),
                "text": str(row[text_column]),
                "timestamp_utc": str(row.get("timestamp_utc", "")),
                "context": row.get("context", {}),
            })

        try:
            # Get next available key
            key = key_manager.get_next_key()
            print(f"  Using {key.key_name} (usage: {key.requests_today}/{quota_rpd})")

            # Call Gemini API
            response = call_gemini_api(
                items=batch_input,
                api_key=key.key_value,
                model=model,
            )

            # Record usage
            key_manager.record_usage(
                key_name=key.key_name,
                requests=1,
                tokens=0,  # TODO: Extract token usage from response
            )

            # Store results
            results.extend(response["results"])

            # Store raw request/response for audit
            if write_raw:
                raw_records.append({
                    "run_id": run_id,
                    "batch_idx": batch_idx,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "key_name": key.key_name,
                    "num_items": len(batch_items),
                    "request": batch_input,
                    "response": response["raw_response"],
                })

            print(f"  ✓ Batch {batch_idx + 1} complete")

        except RuntimeError as e:
            print(f"  ✗ All keys exhausted: {e}")
            print(f"  Marking remaining items with neutral sentiment...")

            # Fill remaining items with neutral sentiment
            for _, row in batch_items.iterrows():
                results.append({
                    "id": str(row[id_column]),
                    "sent_llm": 0.0,
                    "stance": "neutral",
                    "sarcasm": False,
                    "certainty": 0.0,
                    "toxicity": 0.0,
                })

        except Exception as e:
            print(f"  ✗ Error processing batch {batch_idx + 1}: {e}")

            # Fill failed batch with neutral sentiment
            for _, row in batch_items.iterrows():
                results.append({
                    "id": str(row[id_column]),
                    "sent_llm": 0.0,
                    "stance": "neutral",
                    "sarcasm": False,
                    "certainty": 0.0,
                    "toxicity": 0.0,
                })

    # Write raw records to disk
    if write_raw and raw_records:
        today = datetime.now(timezone.utc).date()
        raw_path = f"raw/gemini/date={today}/batch_{run_id}.jsonl"

        # Write as JSONL
        raw_dir = orbit_io.get_data_dir() / Path(raw_path).parent
        raw_dir.mkdir(parents=True, exist_ok=True)

        raw_file = orbit_io.get_data_dir() / raw_path
        with open(raw_file, "w") as f:
            for record in raw_records:
                f.write(json.dumps(record) + "\n")

        print(f"\n✓ Wrote raw request/response to {raw_path}")

    # Merge results back into original DataFrame
    results_df = pd.DataFrame(results)

    # Merge on ID
    output_df = items.copy()
    output_df = output_df.merge(
        results_df,
        left_on=id_column,
        right_on="id",
        how="left",
        suffixes=("", "_gemini"),
    )

    # Fill missing values with neutral
    for col in ["sent_llm", "certainty", "toxicity"]:
        if col in output_df.columns:
            output_df[col] = output_df[col].fillna(0.0)

    if "stance" in output_df.columns:
        output_df["stance"] = output_df["stance"].fillna("neutral")

    if "sarcasm" in output_df.columns:
        output_df["sarcasm"] = output_df["sarcasm"].fillna(False)

    # Log statistics
    key_manager.log_stats()

    print(f"\n✓ Gemini batch scoring complete!")
    print(f"  Total items: {len(output_df)}")
    print(f"  Items with scores: {output_df['sent_llm'].notna().sum()}")
    print(f"  Mean sentiment: {output_df['sent_llm'].mean():.3f}")
    print(f"  Stance distribution:")
    if "stance" in output_df.columns:
        stance_counts = output_df["stance"].value_counts()
        for stance, count in stance_counts.items():
            print(f"    {stance}: {count} ({count/len(output_df)*100:.1f}%)")

    return output_df


if __name__ == "__main__":
    # Example usage / testing
    print("Testing Gemini LLM batching...\n")

    # Create sample data
    sample_data = pd.DataFrame([
        {
            "id": "news_1",
            "text": "Fed holds rates steady amid inflation concerns",
            "timestamp_utc": "2025-01-15T19:00:00Z",
        },
        {
            "id": "news_2",
            "text": "SPY reaches all-time high on strong earnings",
            "timestamp_utc": "2025-01-15T20:00:00Z",
        },
        {
            "id": "reddit_1",
            "text": "SPY gonna rip tomorrow! 🚀",
            "timestamp_utc": "2025-01-15T21:00:00Z",
        },
    ])

    print("Sample data:")
    print(sample_data)

    # Process (requires GEMINI_API_KEY_1 in environment)
    try:
        results = batch_score_gemini(
            items=sample_data,
            batch_size=10,
            write_raw=True,
        )

        print("\nResults:")
        print(results[["id", "text", "sent_llm", "stance", "certainty"]])

    except ValueError as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure to set GEMINI_API_KEY_1 in your .env file")
