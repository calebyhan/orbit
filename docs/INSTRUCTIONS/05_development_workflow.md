# Development Workflow and Best Practices

*Last edited: 2025-11-15*

**Purpose**: Guidelines for contributing to ORBIT, including code organization, documentation standards, and LLM operator guardrails.

---

## Golden Rules (from CLAUDE.md)

Before making any code or docs changes, follow these rules:

1. **Do not create new files** outside `docs/` or `src/` unless a workflow explicitly requires it. Prefer edits **inside `docs/` first**.
2. **Before any command or code change**, read the **relevant `docs/` specs** end-to-end and list the **acceptance checks** you will satisfy.
3. **Point-in-time discipline**: Never use data published after the cutoff; respect lags; do not alter anti-leak rules without updating `docs/` to match.
4. **Minimal diffs**: Keep changes atomic; update the specific module's spec in `docs/` and bump its **last_edited** timestamp.
5. **No silent assumptions**: If a spec is ambiguous, **edit the relevant doc** to clarify, then implement.
6. **Rate limits**: Adhere to `docs/04-data-sources/rate_limits.md`. Use exponential backoff and bounded retries (no tight loops).
7. **Validation first**: Run the module's **acceptance checklist** before/after changes; record results (logs/artifacts).
8. **Security/Compliance**: Follow `tos_compliance.md`; no PII; set a proper `User-Agent` for each external request.

---

## Development Workflow

### Standard Process

1. **Read**: Review `docs/02-architecture/*`, then the target module spec under `docs/05-*` / `06-*` / `07-*` / `08-*`.
2. **Plan**: Draft a brief plan referencing the spec sections you will adhere to.
3. **Implement**: Write code + tests per module spec.
4. **Verify**: Run acceptance checks + backtests defined in `docs/09-evaluation/*`.
5. **Document**: Update the modified doc's **last_edited** timestamp.
6. **Updates**: Mark completed tasks in `docs/11-roadmap/milestones.md` (e.g., `[ ]` → `[x]`).

---

## Directory Structure

### Code Organization

```
src/orbit/
├── __init__.py
├── __main__.py              # CLI entry point
├── ingest/                  # Data ingestion modules
│   ├── prices_stooq.py      # Stooq price ingestion
│   ├── news_ws.py           # Alpaca WebSocket news
│   ├── news_backfill.py     # Alpaca REST API backfill
│   └── llm_gemini.py        # Gemini sentiment scoring
├── preprocessing/           # Data cleaning and normalization
├── features/                # Feature engineering
├── modeling/                # Model training and inference
└── utils/                   # Shared utilities
    ├── config.py            # Configuration management
    ├── io.py                # Parquet I/O helpers
    └── generate_samples.py  # Sample data generator (M0)
```

---

### Documentation Organization

```
docs/
├── 00-glossary/             # Terminology definitions
├── 01-overview/             # Project scope and constraints
├── 02-architecture/         # System design and dataflow
├── 03-config/               # Configuration specifications
├── 04-data-sources/         # External API specs and compliance
├── 05-ingestion/            # Ingestion module specs
├── 06-preprocessing/        # Cleaning and normalization rules
├── 07-features/             # Feature engineering specs
├── 08-modeling/             # Model architecture and training
├── 09-evaluation/           # Backtest rules and metrics
├── 10-operations/           # Production runbooks and monitoring
├── 11-roadmap/              # Milestones and future plans
├── 12-schemas/              # Data schema definitions
├── 98-test-plans/           # Test specifications
├── 99-templates/            # Document templates
└── INSTRUCTIONS/            # Developer onboarding (this directory)
```

---

## Code Standards

### Python Style

Follow PEP 8 with these ORBIT-specific conventions:

```python
# Imports: standard library → third-party → local
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from orbit.utils.config import load_config
from orbit.utils.io import write_parquet

# Constants: UPPER_CASE
DEFAULT_SYMBOLS = ["SPY", "VOO"]
MAX_RETRIES = 5

# Functions: snake_case
def fetch_news_articles(symbol: str, start_date: str) -> pd.DataFrame:
    """
    Fetch news articles for a symbol.

    Args:
        symbol: Ticker symbol (e.g., "SPY")
        start_date: Start date in YYYY-MM-DD format

    Returns:
        DataFrame with columns: id, headline, created_at, symbols
    """
    pass

# Classes: PascalCase
class NewsIngester:
    def __init__(self, api_key: str):
        self.api_key = api_key
```

---

### Type Hints

Use type hints for all function signatures:

```python
from typing import Optional, List, Dict, Any
import pandas as pd

def aggregate_sentiment(
    df: pd.DataFrame,
    group_by: str = "date",
    agg_funcs: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    """Aggregate sentiment scores."""
    if agg_funcs is None:
        agg_funcs = {"sentiment": "mean", "certainty": "mean"}
    return df.groupby(group_by).agg(agg_funcs)
```

---

### Error Handling

Use specific exceptions and meaningful error messages:

```python
import logging

logger = logging.getLogger(__name__)

def load_api_key(key_name: str) -> str:
    """Load API key from environment."""
    key = os.getenv(key_name)
    if not key:
        raise ValueError(
            f"Missing required environment variable: {key_name}\n"
            f"Add it to your .env file. See docs/03-config/env_keys.md"
        )
    return key

def fetch_with_retry(url: str, max_retries: int = 5) -> dict:
    """Fetch URL with exponential backoff."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait = 60 * (2 ** attempt)
                logger.warning(f"Rate limited (429), backing off {wait}s")
                time.sleep(wait)
            elif e.response.status_code in [500, 503]:
                logger.warning(f"Server error ({e.response.status_code}), retrying")
                time.sleep(10)
            else:
                logger.error(f"HTTP error: {e}")
                raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(5)
```

---

### Logging

Use structured logging with appropriate levels:

```python
import logging
from pathlib import Path

# Setup logger (typically in __init__.py or main module)
def setup_logger(name: str, log_dir: Path, level: str = "INFO") -> logging.Logger:
    """Configure logger with file and console handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # File handler
    log_file = log_dir / f"{name}_{datetime.now():%Y%m%d_%H%M%S}.log"
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, level.upper()))

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger

# Usage
logger = setup_logger("orbit.ingest.news", Path("logs"))

logger.debug("Connecting to WebSocket...")
logger.info("Fetched 150 articles for SPY")
logger.warning("Rate limit approaching (180/200 RPM)")
logger.error("Failed to authenticate with Alpaca API")
```

**Log levels:**
- `DEBUG`: Detailed diagnostic info (request/response details)
- `INFO`: Informational messages (progress, milestones)
- `WARNING`: Unexpected but handled events (rate limits, retries)
- `ERROR`: Errors that prevent operation (auth failures, exceptions)

---

## Documentation Standards

### File Headers

Every doc file must have:

```markdown
# Module/Topic Name

*Last edited: YYYY-MM-DD*

**Purpose**: One-sentence description of what this doc covers.
```

**Always update `Last edited` when modifying a doc.**

---

### Acceptance Checklists

Every module spec should include an acceptance checklist:

```markdown
## Acceptance Checklist (M1)

* ✅ Can you ingest prices from Stooq without errors?
* ✅ Can you stream news from Alpaca WebSocket with deduplication?
* [ ] Did you respect the 15:30 ET cutoff and lags?
* [ ] Do ablations show text adds value on burst days?
```

**Mark items as:**
- `[ ]` - Not started
- `[x]` - Completed
- `✅` - Completed and verified
- `🚧` - In progress
- `❌` - Blocked or not applicable

---

### Cross-References

Use relative links between docs:

```markdown
See [rate_limits.md](../04-data-sources/rate_limits.md) for details.

For CLI usage, see [02_cli_commands.md](../INSTRUCTIONS/02_cli_commands.md).
```

---

### Code Examples in Docs

Use fenced code blocks with language specifiers:

````markdown
```python
import pandas as pd

df = pd.read_parquet("data/raw/news/date=2025-11-15/news.parquet")
print(f"Articles: {len(df)}")
```

```bash
# Ingest prices from Stooq
orbit ingest prices

# Stream real-time news
orbit ingest news --symbols SPY VOO
```
````

---

## Git Workflow

### Branching Strategy

```bash
# Main branch (stable, production-ready)
main

# Feature branches (short-lived)
feature/news-websocket-ingestion
feature/gemini-sentiment-scoring

# Bugfix branches
bugfix/rate-limit-handling

# Release branches (when needed)
release/m1
release/m2
```

---

### Commit Messages

Use conventional commit format:

```bash
# Format: <type>(<scope>): <subject>

# Types:
feat: Add new feature
fix: Bug fix
docs: Documentation changes
refactor: Code refactoring
test: Add or update tests
chore: Maintenance tasks

# Examples:
feat(ingest): add Alpaca news WebSocket ingestion
fix(backfill): handle 429 rate limit with exponential backoff
docs(instructions): create developer onboarding guide
refactor(io): extract Parquet write logic to utils
test(news): add unit tests for deduplication
chore(deps): update pandas to 2.0.3
```

---

### Pull Request Process

1. **Create feature branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes**:
   - Update code in `src/`
   - Update docs in `docs/`
   - Add tests in `tests/`

3. **Run tests**:
   ```bash
   pytest tests/ -v
   ```

4. **Update milestones**:
   ```bash
   # Mark tasks as complete in docs/11-roadmap/milestones.md
   vim docs/11-roadmap/milestones.md
   ```

5. **Commit with conventional format**:
   ```bash
   git add .
   git commit -m "feat(features): add news sentiment aggregation"
   ```

6. **Push and create PR**:
   ```bash
   git push origin feature/my-feature
   # Then create PR on GitHub
   ```

---

## Testing Strategy

See [06_testing.md](06_testing.md) for detailed testing guidelines.

**Quick reference:**

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_io.py -v

# Run with coverage
pytest tests/ --cov=src/orbit --cov-report=html

# Run only M0 sample tests (no external APIs)
pytest tests/ -v -m m0
```

---

## Configuration Management

### Environment Variables

Use `.env` for all secrets and environment-specific settings:

```bash
# .env (never commit this file)
ALPACA_API_KEY=secret_key
GEMINI_API_KEY_1=another_secret

ORBIT_DATA_DIR=/srv/orbit/data
ORBIT_LOG_LEVEL=INFO
```

Load in code:

```python
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env automatically

api_key = os.getenv("ALPACA_API_KEY")
data_dir = os.getenv("ORBIT_DATA_DIR", "./data")  # Default fallback
```

---

### YAML Configuration

Use `orbit.yaml` for non-secret settings:

```yaml
# orbit.yaml (can be committed)
symbols:
  - SPY
  - VOO

ingestion:
  news:
    buffer_size: 100
    flush_interval: 300  # seconds

features:
  price:
    lookback_days: 30
  sentiment:
    aggregation: "mean"
```

Load in code:

```python
import yaml

with open("orbit.yaml") as f:
    config = yaml.safe_load(f)

symbols = config["symbols"]
buffer_size = config["ingestion"]["news"]["buffer_size"]
```

---

## Point-in-Time Discipline

ORBIT is a backtesting framework. **Never use future data to predict the past.**

### Cutoff Rules

From `docs/03-config/cutoffs_timezones.md`:

- **News cutoff**: 15:30 ET (to predict next session open at 09:30 ET)
- **Price cutoff**: Previous close (never use intraday prices)
- **Feature lag**: Minimum 1 day (e.g., sentiment on day T predicts returns on T+1)

### Code Examples

```python
# ✅ CORRECT: Use only data published before cutoff
def get_news_for_prediction(date: str) -> pd.DataFrame:
    """Get news published before 15:30 ET on date."""
    cutoff = pd.Timestamp(date).replace(hour=15, minute=30, tz='US/Eastern')
    df = pd.read_parquet(f"data/raw/news/date={date}/news.parquet")
    return df[df["created_at"] <= cutoff]

# ❌ WRONG: Using all news for the day (includes after-hours)
def get_news_for_prediction(date: str) -> pd.DataFrame:
    return pd.read_parquet(f"data/raw/news/date={date}/news.parquet")
```

---

## Security and Compliance

### API Terms of Service

Always comply with data provider TOS:

- **Alpaca**: Free market data, attribution required
- **Gemini**: Free tier for research/personal use
- **Reddit**: OAuth2, rate limits, no commercial use without approval
- **Stooq**: Free historical data, no redistribution

See `docs/04-data-sources/tos_compliance.md` for details.

---

### User-Agent Headers

Set a proper User-Agent for all HTTP requests:

```python
import requests

headers = {
    "User-Agent": os.getenv("ORBIT_USER_AGENT", "ORBIT/1.0")
}

response = requests.get(url, headers=headers)
```

---

### PII and Sensitive Data

**Never log or store:**
- API keys (use environment variables)
- User credentials
- Personal identifiable information (PII)

**Safe logging:**
```python
# ✅ CORRECT: Mask sensitive data
logger.info(f"Using Alpaca key: {api_key[:8]}...")

# ❌ WRONG: Logging full API key
logger.info(f"Using Alpaca key: {api_key}")
```

---

## Performance Optimization

### Parquet I/O

Use Parquet for all data storage (efficient compression and columnar reads):

```python
import pyarrow.parquet as pq

# Write with compression
df.to_parquet(
    "data/features/features_daily.parquet",
    engine="pyarrow",
    compression="snappy",
    index=False
)

# Read specific columns only
df = pd.read_parquet(
    "data/features/features_daily.parquet",
    columns=["date", "symbol", "sentiment_mean"]
)
```

---

### Memory Management

For large datasets, use chunking:

```python
# Read in chunks (for huge files)
chunk_iter = pd.read_parquet(
    "data/raw/news/date=2024-*/news.parquet",
    engine="pyarrow",
    chunksize=10000
)

for chunk in chunk_iter:
    process_chunk(chunk)
```

---

### Rate Limit Respect

Always respect external API rate limits:

```python
import time
from ratelimit import limits, sleep_and_retry

# 200 requests per minute (Alpaca limit)
@sleep_and_retry
@limits(calls=200, period=60)
def fetch_news(symbol: str) -> dict:
    return requests.get(f"{API_URL}/news?symbol={symbol}").json()
```

---

## Escalation

If you need to create a new file or directory outside `docs/` or `src/`:

1. **Propose in docs first**: Add a spec to relevant `docs/` section explaining why existing files are insufficient.
2. **Get approval**: Create a GitHub issue or discuss with maintainers.
3. **Document**: Update `docs/02-architecture/workspace_layout.md` with new directory/file.
4. **Update `.gitignore`**: If the new file/dir should not be committed.

**Example**:
```markdown
## Proposal: Add `scripts/` directory

**Why**: Need standalone scripts for data migration and one-time operations.
**Existing limitations**: `src/orbit/` is for production modules, not ad-hoc scripts.
**Files**:
- `scripts/migrate_legacy_data.py` - One-time migration from old schema
- `scripts/validate_backfill.py` - Validation script for backfill completeness
```

---

## Related Documentation

- [CLAUDE.md](../../CLAUDE.md) - LLM operator guardrails
- [06_testing.md](06_testing.md) - Testing guidelines
- [workspace_layout.md](../02-architecture/workspace_layout.md) - Directory structure
- [tos_compliance.md](../04-data-sources/tos_compliance.md) - API compliance
- [milestones.md](../11-roadmap/milestones.md) - Project roadmap
