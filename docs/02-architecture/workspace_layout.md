# ORBIT — Workspace & Data Layout

*Last edited: 2025-11-10*

This page documents the recommended repo layout, the canonical `src/` package for code, and the shared centralized data location for multi-user development.

## Goals

- Provide a single canonical source tree for the codebase under `src/` so imports are stable (e.g., `import orbit.*`).
- Keep the shared data lake separate from user workspaces at `/srv/orbit/data` (readable by staff/service accounts, writable by ingestion jobs).
- Give each developer a per-user userspace on the Ubuntu host for iterative work and experimentation (examples below).

## Canonical paths

- Code (source): `<repo_root>/src/orbit/...` — this is where application modules, CLI entrypoints, and packages live.
- Tests: `<repo_root>/tests/` — unit/integration tests that import `orbit` from `src/`.
- Local configs: `<repo_root>/config/` (templates live in `docs/99-templates`).
- Centralized data lake (shared): `/srv/orbit/data/` — Parquet tables (e.g., `/srv/orbit/data/raw/`, `/srv/orbit/data/curated/`, `/srv/orbit/data/features/`).
- Per-user userspace on the host: `/home/<user>/orbit/` — clone of the repo or mount with development environment.

## Recommended `src/` layout (start here)

Create a conventional Python package layout under `src/` so imports are unambiguous and packaging is straightforward:

```
repo-root/
├─ src/
│  └─ orbit/
│     ├─ __init__.py
│     ├─ cli.py            # CLI entrypoints: `orbit.ingest`, `orbit.features`, etc.
│     ├─ ingest/
│     │  ├─ __init__.py
│     │  ├─ news.py
│     │  └─ social.py
│     ├─ preprocess/
│     ├─ features/
│     ├─ models/
│     └─ ops/
├─ config/
├─ tests/
├─ docs/
└─ pyproject.toml or setup.cfg
```

Why `src/`? Tools that support `src/` layout (PyPA, tox, pytest) avoid accidental import of the working directory or stale installs. It separates installed package code from repo root artifacts.

## Development workflow (per-user on Ubuntu host)

1. Connect to the Ubuntu host via Tailscale (see below).
2. Create or clone your workspace: `/home/<you>/orbit/` and either:
   - Clone the repo there, or
   - Bind-mount from a local clone via sshfs if you prefer.
3. Create a virtual environment and install dev deps: `python -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'`.
4. Point your runtime/config to the shared data lake: set `ORBIT_DATA_DIR=/srv/orbit/data` or update `config/default.yaml` accordingly.

Example startup script (in your userspace):

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /home/$USER/orbit-workspace

# Create and activate virtual environment
python -m venv .venv
. .venv/bin/activate

# Install ORBIT in editable mode with dependencies
pip install -e '.[dev,parquet]'

# Generate sample data for local testing (optional, runs without external APIs)
python src/orbit/utils/generate_samples.py

# Create .env file with your configuration (automatically loaded by ORBIT)
cp .env.example .env
# Edit .env to set:
#   ORBIT_DATA_DIR=/srv/orbit/data
#   GEMINI_API_KEY_1=...
#   etc.

# No need to manually export! ORBIT automatically loads .env
# Just run commands directly:
orbit ingest prices
```

## Data directory structure

ORBIT uses a **strict separation** between repo-committed sample data and external production data:

| Directory | Location | Purpose | Version Control | Size |
|-----------|----------|---------|-----------------|------|
| **Sample data** | `./data/sample/` | CI/testing, no external APIs | ✅ Committed | Small (~MB) |
| **Production model** | `./data/models/production/` | Latest vetted model for immediate use | ✅ Committed | Small (~MB) |
| **ALL production data** | `/srv/orbit/data/` | All raw, curated, features, scores | ❌ Not committed | Large (GB+) |

**Key design principles:**
- **`./data` contains ONLY sample data and models** - nothing else
- **ALL production/real data lives in `/srv/orbit/data`** exclusively
- **Sample data** (`./data/sample/`) is always used by fixture loaders for testing
- **Production data** location is **always** `/srv/orbit/data` (configurable via `ORBIT_DATA_DIR`)
- Tests and CLI `--local-sample` / `--from-sample` flags use sample data exclusively
- Production runs (M1+) must set `ORBIT_DATA_DIR=/srv/orbit/data` for all I/O operations
- This separation keeps the repo small (~100MB) and avoids accidental commits of large datasets

---

### 1. Local repo data (committed): `<repo_root>/data/`

**ONLY sample data and production models** - nothing else belongs here:

```
<repo_root>/data/
├─ sample/                  # Test fixtures (no external APIs) - ONLY committed data
│  ├─ prices/2024/11/05/
│  │  ├─ SPY.parquet
│  │  ├─ VOO.parquet
│  │  └─ ^SPX.parquet
│  ├─ news/2024/11/05/
│  │  └─ alpaca.parquet
│  ├─ social/2024/11/05/
│  │  └─ reddit.parquet
│  └─ features/2024/11/05/
│     └─ features_daily.parquet
│
└─ models/
   └─ production/           # Latest vetted production model - ONLY committed model
      ├─ heads/
      │  ├─ price/
      │  │  ├─ model.pkl
      │  │  └─ calibrator.pkl
      │  ├─ news/
      │  │  ├─ model.pkl
      │  │  │  └─ calibrator.pkl
      │  └─ social/
      │     ├─ model.pkl
      │     └─ calibrator.pkl
      └─ fusion/
         ├─ fusion_params.json
         └─ calibrator.pkl
```

**Used for:**
- CI pipeline (no external API keys required)
- Local development and testing
- Unit tests and integration tests
- Immediate model inference after repo clone

**Size limits:** Keep repo data <100MB total (use Git LFS if models exceed 10MB each)

**IMPORTANT:** 
- Do **NOT** create `./data/raw/`, `./data/curated/`, `./data/features/`, or `./data/scores/` in the repo
- These directories exist **ONLY** in `/srv/orbit/data/`
- Sample equivalents are under `./data/sample/` only

### 2. Production data lake (external): `/srv/orbit/data/`

**ALL real data** stored centrally (never in repo):

```
/srv/orbit/data/
├─ raw/                     # Raw ingestion - ALL production raw data here
│  ├─ prices/YYYY/MM/DD/*.parquet
│  ├─ news/YYYY/MM/DD/*.parquet
│  ├─ social/YYYY/MM/DD/*.parquet
│  └─ gemini/YYYY/MM/DD/*.json    # Raw LLM req/resp
│
├─ curated/                 # ALL production curated data here
│  ├─ prices/YYYY/MM/DD/*.parquet
│  ├─ news/YYYY/MM/DD/*.parquet
│  └─ social/YYYY/MM/DD/*.parquet
│
├─ features/YYYY/MM/DD/     # ALL production features here
│  └─ features_daily.parquet
│
├─ scores/<run_id>/         # ALL model predictions here
│  └─ scores.parquet
│
├─ models/<run_id>/<window_id>/  # ALL trained model archive here
│  ├─ heads/
│  │  ├─ price/
│  │  ├─ news/
│  │  └─ social/
│  └─ fusion/
│
└─ rejects/                 # ALL rejected records here
   └─ <source>/<reason>/
```

**Used for:**
- **ALL production pipeline runs** (M1+)
- Model training on full historical data
- Backtest experiments
- Model archive and A/B testing
- **This is the ONLY location for real data**

**Setup instructions:**
```bash
# Create centralized data lake (one-time setup)
sudo mkdir -p /srv/orbit/data
sudo chown $USER:$USER /srv/orbit/data

# ALWAYS set this for production runs
export ORBIT_DATA_DIR=/srv/orbit/data

# Add to ~/.bashrc to make permanent
echo 'export ORBIT_DATA_DIR=/srv/orbit/data' >> ~/.bashrc
```

**Critical rule:** If `ORBIT_DATA_DIR` is not set, code defaults to `./data` which should **ONLY** contain sample data. Production runs **MUST** set this variable.

**Permissions recommendation:**
- Data lake owner: `orbit-data` system group
- Ingest and model jobs run under a service account in this group
- Per-user workspaces: owned by user, read access to `/srv/orbit/data` via group membership or POSIX ACLs

## Access via Tailscale

Use Tailscale to securely connect dev machines to the Ubuntu host without exposing ports publicly.

Quick steps:
1. Install Tailscale on the Ubuntu host and on your local machine.
2. Authenticate both to your Tailscale account and ensure they are on the same tailnet.
3. From your local machine: `ssh <tailscale-ip-or-hostname>` into the Ubuntu host (SSH key recommended).
4. Once connected, your per-user workspace is `/home/<user>/orbit-workspace` and the data lake is mounted at `/srv/orbit/data`.

## I/O Contract (M0)

The `orbit.io` module provides standardized utilities for reading and writing Parquet files:

```python
from orbit import io

# Reading data (relative paths resolved from ORBIT_DATA_DIR)
df = io.read_parquet("prices/2024/11/05/SPY.parquet")
df = io.read_parquet("prices/", filters=[("date", ">=", "2024-11-01")])
df = io.read_parquet("prices/2024/11/05/SPY.parquet", columns=["date", "close"])

# Writing data
io.write_parquet(df, "prices/2024/11/05/SPY.parquet")

# Schema validation
errors = io.validate_schema(df, required_columns=["date", "symbol", "close"])

# Load test fixtures (for CI/development - always reads from local data/sample/)
df_prices = io.load_fixtures("prices")     # Loads data/sample/prices/2024/11/05/SPY.parquet
df_news = io.load_fixtures("news")         # Loads data/sample/news/2024/11/05/alpaca.parquet
df_social = io.load_fixtures("social")     # Loads data/sample/social/2024/11/05/reddit.parquet
df_features = io.load_fixtures("features") # Loads data/sample/features/2024/11/05/features_daily.parquet
```

**Key features:**
- **Automatic path resolution** via `ORBIT_DATA_DIR` environment variable (defaults to `./data`)
- **Dual-mode operation:**
  - Development: `ORBIT_DATA_DIR` unset → uses `./data` (includes sample data)
  - Production: `ORBIT_DATA_DIR=/srv/orbit/data` → uses centralized data lake
- **Fixture loaders** always read from local `data/sample/` for testing (no external APIs required)
- **Engine flexibility:** Supports both pyarrow and fastparquet engines (automatically selected)
- **Schema validation** utilities for data quality checks

**CLI commands (M0):**
```bash
# Test with local sample data (no external APIs)
orbit ingest --local-sample
orbit features --from-sample

# These commands use fixtures from ./data/sample/ regardless of ORBIT_DATA_DIR

# Production runs - MUST set ORBIT_DATA_DIR first
export ORBIT_DATA_DIR=/srv/orbit/data
orbit ingest:prices              # Writes to /srv/orbit/data/raw/prices/
orbit features:build --date 2024-11-05  # Reads from /srv/orbit/data/, writes to /srv/orbit/data/features/

# Load production model for inference (always uses ./data/models/production/)
orbit predict --date 2024-11-05 --model production
```
