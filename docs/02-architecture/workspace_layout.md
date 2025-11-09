# ORBIT — Workspace & Data Layout

*Last edited: 2025-11-07*

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
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
export ORBIT_DATA_DIR=/srv/orbit/data
export GEMINI_API_KEY_1=...
```

## `/srv/orbit/data` layout

Use Parquet partitions and a stable prefix for all environments:

```
/srv/orbit/data/
├─ raw/
│  ├─ news/YYYY/MM/DD/*.parquet
│  └─ social/YYYY/MM/DD/*.parquet
├─ curated/
│  ├─ news/YYYY/MM/DD/*.parquet
│  └─ social/YYYY/MM/DD/*.parquet
├─ features/
│  └─ features_daily.parquet
└─ models/
   └─ heads/...
```

Permissions recommendation:
- Data lake owner: `orbit-data` system group. Ingest and model jobs run under a service account in this group.
- Per-user workspaces: owned by user. Grant read access to `/srv/orbit/data` via group membership or POSIX ACLs.

## Access via Tailscale

Use Tailscale to securely connect dev machines to the Ubuntu host without exposing ports publicly.

Quick steps:
1. Install Tailscale on the Ubuntu host and on your local machine.
2. Authenticate both to your Tailscale account and ensure they are on the same tailnet.
3. From your local machine: `ssh <tailscale-ip-or-hostname>` into the Ubuntu host (SSH key recommended).
4. Once connected, your per-user workspace is `/home/<user>/orbit-workspace` and the data lake is mounted at `/srv/orbit/data`.
