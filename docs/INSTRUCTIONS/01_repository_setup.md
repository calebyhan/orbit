# Repository Setup

*Last edited: 2025-11-15*

**Purpose**: Get ORBIT running on your local machine from scratch.

---

## Prerequisites

- **OS**: Unix-like environment (Linux, macOS, WSL on Windows)
- **Python**: 3.11 or higher
- **Git**: For version control
- **Shell**: bash or zsh

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/calebyhan/orbit.git
cd orbit
```

---

## Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate
```

**Note**: You'll need to activate the virtual environment every time you start a new terminal session:
```bash
source .venv/bin/activate
```

---

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs all required packages including:
- `click` - CLI framework
- `pandas` - Data manipulation
- `pyarrow` - Parquet file support
- `requests` - HTTP client
- `websocket-client` - WebSocket support
- `python-dotenv` - Environment variable management
- `tqdm` - Progress bars
- `google-generativeai` - Gemini API client

---

## Step 4: Verify Installation

```bash
# Check that the CLI is available
orbit --help

# Should output:
# usage: orbit [-h] {ingest,features} ...
# ORBIT - Options Research Based on Integrated Textual data
```

---

## Step 5: Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your preferred editor. See [03_api_keys_configuration.md](03_api_keys_configuration.md) for detailed API key setup.

**Minimal configuration for M0 (offline mode, no APIs needed):**
```bash
ORBIT_DATA_DIR=./data
ORBIT_USER_AGENT=ORBIT/1.0
ORBIT_LOG_LEVEL=INFO
```

---

## Step 6: Create Configuration File

```bash
# Copy the sample config
cp docs/03-config/sample_config.yaml orbit.yaml

# Edit paths and settings as needed
# For most users, the defaults are fine
```

**Key settings in `orbit.yaml`:**
- Data directory paths
- Symbol configurations
- Ingestion parameters
- Feature engineering settings

---

## Step 7: Directory Structure

ORBIT will create the following directories automatically when you run commands:

```
orbit/
├── data/               # Data storage (configurable via ORBIT_DATA_DIR)
│   ├── raw/           # Raw ingested data
│   │   ├── prices/    # OHLCV from Stooq
│   │   ├── news/      # News from Alpaca (partitioned by date)
│   │   └── gemini/    # LLM sentiment analysis results
│   ├── curated/       # Cleaned/normalized data
│   └── features/      # Engineered features for modeling
├── reports/           # Backtest reports and analysis
└── logs/              # Application logs
```

See [workspace_layout.md](../02-architecture/workspace_layout.md) for detailed directory specifications.

---

## Step 8: Verify Setup (M0 Mode - No APIs Required)

Test your installation without external API dependencies:

```bash
# Generate synthetic sample data
python src/orbit/utils/generate_samples.py

# Run M0 CLI commands (offline mode)
orbit ingest --local-sample
orbit features --from-sample

# Run unit tests
pytest tests/ -v
```

If all tests pass, your environment is ready!

---

## Next Steps

1. **Configure API Keys**: See [03_api_keys_configuration.md](03_api_keys_configuration.md)
2. **Learn CLI Commands**: See [02_cli_commands.md](02_cli_commands.md)
3. **Run Historical Backfill**: See [04_historical_backfill.md](04_historical_backfill.md)

---

## Troubleshooting

### Python Version Issues

```bash
# Check your Python version
python3 --version

# If < 3.11, install a newer version
# On Ubuntu/Debian:
sudo apt update
sudo apt install python3.11 python3.11-venv

# Then recreate the venv with the new version
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Virtual Environment Not Activating

```bash
# If 'source' doesn't work, try:
. .venv/bin/activate

# On Windows WSL, ensure you're using bash/zsh, not Windows cmd/PowerShell
```

### Permission Errors

```bash
# If you get permission errors with /srv/orbit/data:
# Option 1: Use local data directory instead
echo "ORBIT_DATA_DIR=./data" >> .env

# Option 2: Create /srv/orbit with proper permissions
sudo mkdir -p /srv/orbit/data
sudo chown $USER:$USER /srv/orbit/data
```

### Import Errors

```bash
# Ensure venv is activated (should see (.venv) in prompt)
source .venv/bin/activate

# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Verify installation
pip list | grep -E "click|pandas|pyarrow"
```

---

## Clean Reinstall

If you encounter persistent issues:

```bash
# Remove virtual environment
rm -rf .venv

# Remove any cached Python files
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete

# Start fresh from Step 2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Related Documentation

- [workspace_layout.md](../02-architecture/workspace_layout.md) - Directory structure details
- [config_reconciliation.md](../03-config/config_reconciliation.md) - Configuration file specs
- [02_cli_commands.md](02_cli_commands.md) - Command reference
