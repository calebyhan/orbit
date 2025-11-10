# ORBIT — Workspace & Data Layout

*Last edited: 2025-11-09*

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

# Configure data directory for production use
export ORBIT_DATA_DIR=/srv/orbit/data
export GEMINI_API_KEY_1=...

# Or for local development/testing, omit ORBIT_DATA_DIR to use ./data
```

## Data directory structure

ORBIT uses a **dual-directory architecture** to separate sample/test data from production data:

| Directory | Location | Purpose | Version Control | ORBIT_DATA_DIR |
|-----------|----------|---------|-----------------|----------------|
| **Sample data** | `./data/sample/` | CI/testing, no external APIs | ✅ Committed | ❌ Ignored |
| **Production data** | `/srv/orbit/data/` | Live ingestion, features, models | ❌ Not committed | ✅ Configured |

**Key design principles:**
- **Sample data** (`./data/sample/`) is always used by fixture loaders, regardless of `ORBIT_DATA_DIR`
- **Production data** location is configured via `ORBIT_DATA_DIR` environment variable
- Tests and CLI `--local-sample` / `--from-sample` flags use sample data exclusively
- Production runs (coming in M1) respect `ORBIT_DATA_DIR` for all I/O operations

---

### 1. Local sample data (for CI/development): `<repo_root>/data/sample/`

Sample data stays in the repository for testing without external APIs:

```
<repo_root>/data/
└─ sample/
   ├─ prices/2024/11/05/
   │  ├─ SPY.parquet
   │  ├─ VOO.parquet
   │  └─ ^SPX.parquet
   ├─ news/2024/11/05/
   │  └─ alpaca.parquet
   ├─ social/2024/11/05/
   │  └─ reddit.parquet
   └─ features/2024/11/05/
      └─ features_daily.parquet
```

**Used for:**
- CI pipeline (no external API keys required)
- Local development and testing
- Unit tests and integration tests

### 2. Production data lake: `/srv/orbit/data/`

Production and live data stored centrally:

```
/srv/orbit/data/
├─ raw/
│  ├─ prices/YYYY/MM/DD/*.parquet
│  ├─ news/YYYY/MM/DD/*.parquet
│  └─ social/YYYY/MM/DD/*.parquet
├─ curated/
│  ├─ prices/YYYY/MM/DD/*.parquet
│  ├─ news/YYYY/MM/DD/*.parquet
│  └─ social/YYYY/MM/DD/*.parquet
├─ features/YYYY/MM/DD/
│  └─ features_daily.parquet
├─ scores/<run_id>/
│  └─ scores.parquet
├─ models/<run_id>/<window_id>/
│  ├─ heads/
│  └─ fusion/
└─ rejects/
   └─ <source>/<reason>/
```

**Setup instructions:**
```bash
# Create centralized data lake
sudo mkdir -p /srv/orbit/data
sudo chown $USER:$USER /srv/orbit/data

# Configure environment to use it
export ORBIT_DATA_DIR=/srv/orbit/data

# Or add to ~/.bashrc
echo 'export ORBIT_DATA_DIR=/srv/orbit/data' >> ~/.bashrc
```

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

# These commands use fixtures from data/sample/ regardless of ORBIT_DATA_DIR
```
