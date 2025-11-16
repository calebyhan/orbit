# ORBIT Developer Instructions

*Last edited: 2025-11-15*

**Purpose**: Comprehensive developer onboarding and usage guide for ORBIT.

---

## Quick Start

New to ORBIT? Follow these guides in order:

1. **[Repository Setup](01_repository_setup.md)** - Clone, install dependencies, verify installation
2. **[API Keys Configuration](03_api_keys_configuration.md)** - Get and configure API keys (Alpaca, Gemini)
3. **[CLI Commands](02_cli_commands.md)** - Learn all available commands
4. **[Historical Backfill](04_historical_backfill.md)** - Bootstrap 10 years of news data

**Time to first working setup**: ~2-3 hours (including historical backfill)

---

## Documentation Index

### Getting Started

| Guide | Description | Time Required |
|-------|-------------|---------------|
| [01_repository_setup.md](01_repository_setup.md) | Clone repo, setup venv, install dependencies | 10 minutes |
| [03_api_keys_configuration.md](03_api_keys_configuration.md) | Get API keys from Alpaca, Gemini, Reddit | 15 minutes |
| [02_cli_commands.md](02_cli_commands.md) | Complete CLI reference with examples | 20 minutes read |

### Data Collection

| Guide | Description | Time Required |
|-------|-------------|---------------|
| [04_historical_backfill.md](04_historical_backfill.md) | Fetch 10 years of historical news | 1-2 hours (single key) |
| [02_cli_commands.md#orbit-ingest-news](02_cli_commands.md#orbit-ingest-news) | Stream real-time news | Continuous (daemon) |

### Development

| Guide | Description | Audience |
|-------|-------------|----------|
| [05_development_workflow.md](05_development_workflow.md) | Code standards, git workflow, best practices | Contributors |
| [06_testing.md](06_testing.md) | Testing strategy, writing tests, CI/CD | Contributors |

---

## Common Workflows

### First-Time Setup (M1)

```bash
# 1. Clone and setup
git clone https://github.com/calebyhan/orbit.git
cd orbit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys (see 03_api_keys_configuration.md)

# 3. Ingest historical prices (~1 minute)
orbit ingest prices

# 4. Backfill historical news (~1-2 hours with single key)
orbit ingest news-backfill \
  --start 2015-01-01 \
  --end $(date +%Y-%m-%d) \
  --symbols SPY VOO

# 5. Start real-time news stream (run in tmux/screen)
tmux new -s news-stream
orbit ingest news --symbols SPY VOO
# Detach: Ctrl+B, then D
```

**Total time**: ~2-3 hours (mostly waiting for backfill)

---

### Daily Operations (M1)

```bash
# Morning: Check real-time news stream is running
tmux attach -t news-stream

# After market close: Update prices
orbit ingest prices

# M2+: Build features, train model, generate predictions
# orbit features build --incremental
# orbit train fit --daily
```

---

### Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes
# - Update code in src/
# - Update docs in docs/
# - Add tests in tests/

# 3. Run tests
pytest tests/ -v

# 4. Update milestones
vim docs/11-roadmap/milestones.md

# 5. Commit and push
git add .
git commit -m "feat(module): description"
git push origin feature/my-feature

# 6. Create pull request on GitHub
```

See [05_development_workflow.md](05_development_workflow.md) for details.

---

### M0 Mode (No External APIs)

For rapid testing without API keys:

```bash
# Generate synthetic sample data
python src/orbit/utils/generate_samples.py

# Run M0 commands (offline mode)
orbit ingest --local-sample
orbit features --from-sample

# Run unit tests
pytest tests/ -v -m m0
```

---

## ORBIT Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      ORBIT Pipeline                         │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐
│ Data Sources │
├──────────────┤
│ • Stooq      │ (OHLCV prices, free)
│ • Alpaca     │ (News via WebSocket/REST, free)
│ • Gemini     │ (LLM sentiment, free)
│ • Reddit     │ (Social posts, coming soon)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Ingestion   │ (M1 - 75% complete)
├──────────────┤
│ orbit ingest prices          │ ✅ Stooq OHLCV
│ orbit ingest news            │ ✅ Alpaca WebSocket
│ orbit ingest news-backfill   │ ✅ Alpaca REST API
│ llm_gemini.py                │ ✅ Sentiment scoring
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Raw Storage  │
├──────────────┤
│ data/raw/prices/     │ Parquet, by symbol
│ data/raw/news/       │ Parquet, partitioned by date
│ data/raw/gemini/     │ JSONL, audit trail
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Preprocessing │ (M2 - planned)
├──────────────┤
│ • Deduplication     │
│ • Time alignment    │
│ • Quality filters   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Features   │ (M2 - planned)
├──────────────┤
│ orbit features build         │
│ • Price: returns, volatility │
│ • News: sentiment Z-scores   │
│ • Social: post count, engagement │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Modeling   │ (M3 - planned)
├──────────────┤
│ orbit train fit              │
│ • Price head    │
│ • News head     │
│ • Social head   │
│ • Gated fusion  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Backtesting │ (M3 - planned)
├──────────────┤
│ orbit backtest run           │
│ • Long/flat only            │
│ • Risk controls             │
│ • Ablation studies          │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Reports    │
├──────────────┤
│ reports/backtest_YYYYMMDD/  │
│ • Metrics: Sharpe, Calmar   │
│ • Plots: equity curve, DD   │
└──────────────┘
```

**Current status**: M1 (data gathering + Gemini integration, 75% complete)

See [system_diagram.md](../02-architecture/system_diagram.md) for detailed architecture.

---

## Key Concepts

### Point-in-Time Discipline

ORBIT is a **backtesting framework**. All features must respect temporal ordering:

- **News cutoff**: 15:30 ET (to predict next session)
- **Price cutoff**: Previous close (no intraday data)
- **Feature lag**: Minimum 1 day

See [cutoffs_timezones.md](../03-config/cutoffs_timezones.md)

---

### Tri-Modal Alpha

ORBIT combines three data modalities:

1. **Prices**: Stooq OHLCV (SPY, VOO, ^SPX)
2. **News**: Alpaca news feed with Gemini sentiment
3. **Social**: Reddit posts (r/stocks, r/investing, r/wallstreetbets)

**Gating mechanism**: Text (news/social) is up-weighted only on high-volume days.

See [fusion_gated_blend.md](../08-modeling/fusion_gated_blend.md)

---

### Design Contracts

From [README.md](../../README.md):

1. **Cutoff**: Only use text published ≤ 15:30 ET
2. **Point-in-time**: No revised data; store raw ingests
3. **Gating**: Up-weight text when `news_count_z` or `post_count_z` is high
4. **Ablations required**: Price-only vs +News vs +Social vs All

---

## File Organization

```
orbit/
├── src/orbit/              # Python source code
├── docs/                   # Documentation
│   ├── INSTRUCTIONS/       # Developer guides (this directory)
│   ├── 01-overview/        # Project scope
│   ├── 02-architecture/    # System design
│   ├── 03-config/          # Configuration specs
│   ├── 04-data-sources/    # API specs
│   ├── 05-ingestion/       # Ingestion modules
│   ├── 06-preprocessing/   # Cleaning rules
│   ├── 07-features/        # Feature engineering
│   ├── 08-modeling/        # Model architecture
│   ├── 09-evaluation/      # Backtest rules
│   ├── 10-operations/      # Production runbooks
│   └── 11-roadmap/         # Milestones
├── tests/                  # Unit and integration tests
├── data/                   # Data storage (gitignored)
├── reports/                # Backtest reports (gitignored)
├── logs/                   # Application logs (gitignored)
├── .env                    # Environment variables (gitignored)
├── orbit.yaml              # Configuration file
└── README.md               # Project README
```

See [workspace_layout.md](../02-architecture/workspace_layout.md)

---

## API Key Summary

| Service | Purpose | Free Tier | Keys Needed | M1 Status |
|---------|---------|-----------|-------------|-----------|
| **Stooq** | Price data (OHLCV) | FREE (no key) | 0 | ✅ Required |
| **Alpaca** | News (WebSocket + REST) | FREE | 1-5 | ✅ Required |
| **Gemini** | Sentiment (LLM) | 1,000 RPD/key | 1-5 | ✅ Required |
| **Reddit** | Social posts | 60 RPM | 1 | 🚧 Coming soon |

**Total cost**: $0/month (all free tiers)

See [03_api_keys_configuration.md](03_api_keys_configuration.md) for setup instructions.

---

## Testing Strategy

| Test Type | Command | Coverage |
|-----------|---------|----------|
| **Unit tests** | `pytest tests/ -v` | Individual functions |
| **Integration tests** | `pytest tests/ -v -m integration` | Full pipeline |
| **M0 tests** | `pytest tests/ -v -m m0` | Offline mode (no APIs) |
| **Coverage report** | `pytest tests/ --cov=src/orbit --cov-report=html` | Code coverage |

See [06_testing.md](06_testing.md) for detailed testing guide.

---

## Support and Resources

### Documentation

- **Architecture**: [docs/02-architecture/](../02-architecture/)
- **Specifications**: [docs/05-ingestion/](../05-ingestion/), [docs/07-features/](../07-features/), [docs/08-modeling/](../08-modeling/)
- **Operations**: [docs/10-operations/](../10-operations/)
- **Roadmap**: [docs/11-roadmap/milestones.md](../11-roadmap/milestones.md)

### LLM Operator Guide

If you're an LLM agent (Claude/ChatGPT/etc.) working on ORBIT:

**Read [CLAUDE.md](../../CLAUDE.md) first** - contains critical guardrails and workflows.

### Troubleshooting

- **Setup issues**: [01_repository_setup.md#troubleshooting](01_repository_setup.md#troubleshooting)
- **API errors**: [03_api_keys_configuration.md#troubleshooting](03_api_keys_configuration.md#troubleshooting)
- **Backfill issues**: [04_historical_backfill.md#troubleshooting](04_historical_backfill.md#troubleshooting)
- **Operations playbook**: [failure_modes_playbook.md](../10-operations/failure_modes_playbook.md)

---

## Contributing

ORBIT follows strict development practices to maintain reproducibility and prevent lookahead bias.

**Before contributing:**

1. Read [05_development_workflow.md](05_development_workflow.md) - Golden rules and workflow
2. Review relevant specs in [docs/](../)
3. Write tests (see [06_testing.md](06_testing.md))
4. Update documentation and bump `Last edited` timestamps
5. Mark tasks complete in [milestones.md](../11-roadmap/milestones.md)

**Pull request checklist:**

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Documentation updated (spec + `Last edited` timestamp)
- [ ] Acceptance checklist validated
- [ ] Milestone tasks marked complete
- [ ] Conventional commit format (`feat:`, `fix:`, `docs:`, etc.)

---

## What's Next?

### M1 (75% complete - Current)

- ✅ Stooq price ingestion
- ✅ Alpaca news WebSocket + REST backfill
- ✅ Gemini sentiment scoring with multi-key rotation
- 🚧 Reddit social ingestion

### M2 (Planned)

- Preprocessing: deduplication, time alignment, quality filters
- Feature engineering: price features, news features, social features
- Feature storage: `data/features/features_daily.parquet`

### M3 (Planned)

- Model training: tri-modal heads + gated fusion
- Backtesting: walk-forward validation, ablation studies
- Evaluation: Sharpe ratio, Calmar ratio, regime analysis

See [milestones.md](../11-roadmap/milestones.md) for full roadmap.

---

## Quick Links

- [Main README](../../README.md) - Project overview
- [CLAUDE.md](../../CLAUDE.md) - LLM operator guardrails
- [Milestones](../11-roadmap/milestones.md) - Project roadmap
- [Architecture](../02-architecture/system_diagram.md) - System design
- [Glossary](../00-glossary/glossary.md) - Terminology

---

*For questions or issues, please file a GitHub issue or consult the relevant documentation in `docs/`.*
