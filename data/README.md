# ORBIT Data Directory (./data)

*Last updated: 2025-11-10*

**This directory contains ONLY:**

1. **Sample data** (`./data/sample/`) - Test fixtures for CI/development (no external APIs)
2. **Production model** (`./data/models/production/`) - Latest vetted model

**This directory should NEVER contain:**

❌ `./data/raw/` - Raw ingestion data  
❌ `./data/curated/` - Curated data  
❌ `./data/features/` - Engineered features  
❌ `./data/scores/` - Model predictions  
❌ `./data/rejects/` - Rejected records  
❌ `./data/models/` (except production/) - Model archives

## Where does production data go?

**ALL production data lives in `/srv/orbit/data/`**

Set this in your `.env` file (automatically loaded by ORBIT):

```bash
# In .env file
ORBIT_DATA_DIR=/srv/orbit/data
```

## Directory Structure

```
./data/
├── sample/                 # ✅ Sample data (committed)
│   ├── prices/
│   ├── news/
│   ├── social/
│   └── features/
└── models/
    └── production/         # ✅ Production model (committed)
        ├── heads/
        └── fusion/
```

## Production Data Structure

```
/srv/orbit/data/
├── raw/                    # ✅ ALL raw data here
├── curated/                # ✅ ALL curated data here
├── features/               # ✅ ALL features here
├── scores/                 # ✅ ALL predictions here
├── models/                 # ✅ ALL model archives here
└── rejects/                # ✅ ALL rejected records here
```

## Related Documentation

- `docs/02-architecture/workspace_layout.md` - Full workspace structure
- `docs/05-ingestion/storage_layout_parquet.md` - Storage conventions
- `.gitignore` - What's excluded from version control

## Running Commands

**Setup (one-time):**
```bash
# Create .env file with your configuration
cp .env.example .env
# Edit .env and set ORBIT_DATA_DIR=/srv/orbit/data
# ORBIT automatically loads .env - no manual export needed!
```

**For testing (uses sample data):**
```bash
orbit ingest --local-sample
orbit features --from-sample
```

**For production (uses /srv/orbit/data from .env):**
```bash
# .env is automatically loaded with ORBIT_DATA_DIR=/srv/orbit/data
orbit ingest prices
orbit features:build --date 2024-11-05
```

**Alternative: Manual export (if not using .env):**
```bash
export ORBIT_DATA_DIR=/srv/orbit/data
orbit ingest prices
```
