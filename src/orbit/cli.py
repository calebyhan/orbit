"""CLI entrypoints for ORBIT.

Provides minimal entrypoints for M0: ingest and features commands.
"""

import argparse
import sys
from pathlib import Path


def cmd_ingest_local_sample():
    """Run ingestion on local sample data (M0 deliverable).

    Sample data is always loaded from ./data/sample/ regardless of ORBIT_DATA_DIR.
    This enables testing without external APIs or production data setup.
    """
    from orbit import io

    print("Running ingest with local sample data...")
    print(f"Sample data location: ./data/sample/")
    print(f"Production data location (ORBIT_DATA_DIR): {io.get_data_dir()}")

    # Load and display sample data to verify it works
    try:
        df_prices = io.load_fixtures("prices")
        df_news = io.load_fixtures("news")
        df_social = io.load_fixtures("social")

        print(f"\n✓ Loaded sample prices: {len(df_prices)} rows (from ./data/sample/)")
        print(f"✓ Loaded sample news: {len(df_news)} rows (from ./data/sample/)")
        print(f"✓ Loaded sample social: {len(df_social)} rows (from ./data/sample/)")

        print("\nSample price data:")
        print(df_prices[["date", "symbol", "close"]].to_string())

        print("\n✓ Ingest --local-sample completed successfully!")
        print("\nNote: This command uses sample data from ./data/sample/")
        print("      For production ingestion, use 'orbit ingest' (coming in M1)")
        return 0

    except Exception as e:
        print(f"✗ Error during ingest: {e}", file=sys.stderr)
        print("\nHint: Run 'python src/orbit/utils/generate_samples.py' to create sample data", file=sys.stderr)
        return 1


def cmd_features_from_sample():
    """Build features from sample data (M0 deliverable).

    Sample data is always loaded from ./data/sample/ regardless of ORBIT_DATA_DIR.
    This enables testing without external APIs or production data setup.
    """
    from orbit import io

    print("Building features from sample data...")
    print(f"Sample data location: ./data/sample/")
    print(f"Production data location (ORBIT_DATA_DIR): {io.get_data_dir()}")

    try:
        # Load sample feature data
        df_features = io.load_fixtures("features")

        print(f"\n✓ Loaded sample features: {len(df_features)} rows (from ./data/sample/)")
        print(f"✓ Feature count: {len(df_features.columns)} columns")

        print("\nFeature summary:")
        print(f"  Date: {df_features['date'].iloc[0]}")
        print(f"  Symbol: {df_features['symbol'].iloc[0]}")
        print(f"  Data completeness: {df_features['data_completeness'].iloc[0]:.2%}")

        # Display a few key features
        key_features = [
            "momentum_5d", "momentum_20d",
            "news_count_1d", "news_sentiment_mean",
            "post_count_1d", "social_sentiment_mean"
        ]
        print("\nKey feature values:")
        for feat in key_features:
            if feat in df_features.columns:
                print(f"  {feat}: {df_features[feat].iloc[0]}")

        print("\n✓ Features --from-sample completed successfully!")
        print("\nNote: This command uses sample data from ./data/sample/")
        print("      For production features, use 'orbit features' (coming in M1)")
        return 0

    except Exception as e:
        print(f"✗ Error building features: {e}", file=sys.stderr)
        print("\nHint: Run 'python src/orbit/utils/generate_samples.py' to create sample data", file=sys.stderr)
        return 1


def main(argv=None):
    """Main CLI entrypoint."""
    argv = argv or sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="orbit",
        description="ORBIT - Options Research Based on Integrated Textual data"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ingest command
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Run data ingestion",
        description="Ingest data from various sources into ORBIT"
    )
    ingest_parser.add_argument(
        "--local-sample",
        action="store_true",
        help="Use sample data from ./data/sample/ (M0 mode - no external APIs, no ORBIT_DATA_DIR dependency)"
    )

    # features command
    features_parser = subparsers.add_parser(
        "features",
        help="Build features",
        description="Build feature tables from ingested data"
    )
    features_parser.add_argument(
        "--from-sample",
        action="store_true",
        help="Use sample data from ./data/sample/ (M0 mode - no external APIs, no ORBIT_DATA_DIR dependency)"
    )

    args = parser.parse_args(argv)

    # Handle commands
    if args.command == "ingest":
        if args.local_sample:
            return cmd_ingest_local_sample()
        else:
            print("Error: --local-sample is required for M0", file=sys.stderr)
            print("Usage: orbit ingest --local-sample", file=sys.stderr)
            return 1

    elif args.command == "features":
        if args.from_sample:
            return cmd_features_from_sample()
        else:
            print("Error: --from-sample is required for M0", file=sys.stderr)
            print("Usage: orbit features --from-sample", file=sys.stderr)
            return 1

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
