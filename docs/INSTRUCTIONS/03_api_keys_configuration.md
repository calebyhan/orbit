# API Keys Configuration

*Last edited: 2025-11-15*

**Purpose**: Step-by-step guide to obtaining and configuring API keys for ORBIT.

---

## Overview

ORBIT requires API keys for:

| Service | Purpose | Cost | Keys Required | M1 Status |
|---------|---------|------|---------------|-----------|
| **Alpaca** | News data (WebSocket + REST) | FREE | 1-5 keys | ✅ Required |
| **Gemini** | Sentiment analysis (LLM) | FREE | 1-5 keys | ✅ Required |
| **Reddit** | Social media posts | FREE | 1 key | 🚧 Coming soon |
| **Stooq** | Price data (OHLCV) | FREE | None (public) | ✅ No key needed |

**Note**: All required services have generous FREE tiers suitable for ORBIT's needs.

---

## Environment File Setup

ORBIT uses a `.env` file in the project root for all API keys and configuration:

```bash
# Create .env from template
cp .env.example .env

# Edit with your preferred editor
nano .env    # or vim, code, etc.
```

**Important**:
- `.env` is in `.gitignore` - never commit API keys to version control
- ORBIT automatically loads `.env` when you run any command
- No need to manually export environment variables

---

## Alpaca API Keys

### What is Alpaca?

Alpaca is a commission-free trading platform that provides **free market data** via WebSocket and REST APIs.

**ORBIT uses Alpaca for:**
- Real-time news streaming (WebSocket)
- Historical news backfill (REST API)

**Rate limits (free tier):**
- WebSocket: Real-time streaming, up to 30 symbols
- REST API: 200 requests per minute per key

---

### Get Alpaca API Keys

1. **Sign up**: https://alpaca.markets
   - Click "Get Started for Free"
   - Choose "Individual" account type
   - Complete email verification

2. **Generate API keys**:
   - Log in to dashboard
   - Go to "Paper Trading" (not live trading)
   - Navigate to "API Keys" section
   - Click "Generate New Key"
   - **Important**: Copy both `Key ID` and `Secret Key` immediately (Secret Key only shown once)

3. **Add to `.env`**:

```bash
# For WebSocket real-time streaming (orbit ingest news)
ALPACA_API_KEY=your_key_id_here
ALPACA_API_SECRET=your_secret_key_here

# For REST API historical backfill (orbit ingest news-backfill)
# You can use the same key as WebSocket, or create separate keys
ALPACA_API_KEY_1=your_key_id_here
ALPACA_API_SECRET_1=your_secret_key_here
```

---

### Single Key vs Multi-Key Setup

**Option 1: Single Key (Recommended for most users)**

Simplest setup - use the same key for both WebSocket and REST:

```bash
# In .env:
ALPACA_API_KEY=PK1234567890ABCDEF
ALPACA_API_SECRET=abcdef1234567890
ALPACA_API_KEY_1=PK1234567890ABCDEF
ALPACA_API_SECRET_1=abcdef1234567890
```

**Timeline:**
- Historical backfill (10 years): 1-2 hours
- Real-time streaming: No rate limit impact

**Best for:**
- Initial setup and testing
- Personal research projects
- One-time historical bootstrap

---

**Option 2: Separate Keys (Better rate limit isolation)**

Use different keys for WebSocket vs REST:

```bash
# WebSocket streaming (non-numbered)
ALPACA_API_KEY=PK_websocket_key
ALPACA_API_SECRET=secret_websocket

# REST API (numbered)
ALPACA_API_KEY_1=PK_rest_key_1
ALPACA_API_SECRET_1=secret_rest_1
```

**Why separate?**
- WebSocket and REST have independent rate limits
- Historical backfill won't interfere with real-time streaming
- Easier to monitor usage per endpoint

---

**Option 3: Multi-Key (5x faster backfill)**

Add up to 5 REST API keys for parallel backfill:

```bash
# WebSocket (single key)
ALPACA_API_KEY=PK_websocket
ALPACA_API_SECRET=secret_websocket

# REST API (up to 5 keys for round-robin rotation)
ALPACA_API_KEY_1=PK_key_1
ALPACA_API_SECRET_1=secret_1
ALPACA_API_KEY_2=PK_key_2
ALPACA_API_SECRET_2=secret_2
ALPACA_API_KEY_3=PK_key_3
ALPACA_API_SECRET_3=secret_3
ALPACA_API_KEY_4=PK_key_4
ALPACA_API_SECRET_4=secret_4
ALPACA_API_KEY_5=PK_key_5
ALPACA_API_SECRET_5=secret_5
```

**Timeline:**
- Historical backfill (10 years): 15-20 minutes (vs 1-2 hours with single key)
- Combined throughput: ~950 RPM (5 × 190 RPM)

**Best for:**
- Frequent re-ingestion during development
- CI/CD pipelines with time constraints
- Research requiring rapid iteration

**How to get multiple keys:**
- You can create multiple Alpaca accounts with different emails
- Or request additional API keys from Alpaca support

---

### Verify Alpaca Keys

```bash
# Test WebSocket connection
orbit ingest news --symbols SPY --help

# Test REST API (dry-run a single day)
orbit ingest news-backfill \
  --start 2024-01-01 \
  --end 2024-01-01 \
  --symbols SPY
```

If keys are invalid, you'll see:
```
ERROR: Alpaca authentication failed (401)
Check your ALPACA_API_KEY and ALPACA_API_SECRET in .env
```

---

## Gemini API Keys

### What is Gemini?

Google's Gemini is a large language model API used by ORBIT for **sentiment analysis** of news articles.

**ORBIT uses Gemini for:**
- Scoring news article sentiment: -1 (bearish) to +1 (bullish)
- Stance classification: bull/bear/neutral
- Certainty estimation: 0 (uncertain) to 1 (confident)

**Model**: `gemini-2.5-flash-lite`
**Rate limits (free tier per key):**
- 15 requests per minute (RPM)
- 250,000 tokens per minute (TPM)
- 1,000 requests per day (RPD)

---

### Get Gemini API Keys

1. **Sign up**: https://makersuite.google.com/app/apikey
   - Log in with Google account
   - Accept terms of service

2. **Create API key**:
   - Click "Create API Key"
   - Select a Google Cloud project (or create new one)
   - Click "Create API key in existing project"
   - **Copy the API key** (starts with `AIza...`)

3. **Add to `.env`**:

```bash
# Single key (sufficient for ~50-80 news items/day)
GEMINI_API_KEY_1=AIzaSyABC123...your_key_here
```

---

### Single Key vs Multi-Key Setup

**Option 1: Single Key (Sufficient for most users)**

```bash
GEMINI_API_KEY_1=AIzaSyABC123...
```

**Capacity:**
- 1,000 requests per day
- ~50-80 news articles per day for SPY/VOO (typical volume)
- Processes entire day's news in ~5-10 minutes

**Best for:**
- Daily sentiment scoring
- Production use with SPY/VOO only
- Cost-conscious users (completely FREE)

---

**Option 2: Multi-Key (5x throughput)**

```bash
GEMINI_API_KEY_1=AIzaSyABC123...
GEMINI_API_KEY_2=AIzaSyDEF456...
GEMINI_API_KEY_3=AIzaSyGHI789...
GEMINI_API_KEY_4=AIzaSyJKL012...
GEMINI_API_KEY_5=AIzaSyMNO345...
```

**Capacity:**
- 5,000 requests per day (5 × 1,000)
- Handles 250-400 news items per day
- Processes large backlogs faster

**Best for:**
- Historical backfill sentiment scoring
- Multiple symbols beyond SPY/VOO
- Research with high news volume days

**How to get multiple keys:**
- Create multiple Google accounts
- Generate one API key per account
- All keys use the same free tier limits

---

### Quota Management

Gemini quotas reset daily at **00:00 Pacific Time** (PT).

ORBIT automatically:
- Tracks per-key quota usage
- Rotates between keys (round-robin or least-used)
- Falls back to neutral sentiment when quota exhausted
- Logs quota exhaustion events

**Monitor quota usage:**
```bash
# Check logs for quota warnings
grep -i "quota" logs/gemini_*.log

# Example output:
# 2025-11-15 14:23:45 WARNING - Gemini key 1 quota exhausted (1,000/1,000 RPD)
# 2025-11-15 14:23:45 INFO - Switching to key 2
```

---

### Verify Gemini Keys

```bash
# Test a single sentiment request
python -c "
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY_1'))
model = genai.GenerativeModel('gemini-2.0-flash-exp')
response = model.generate_content('Say hello')
print(response.text)
"
```

Expected output:
```
Hello! 👋 How can I help you today?
```

If key is invalid:
```
google.api_core.exceptions.PermissionDenied: 403 API key not valid
```

---

## Reddit API Keys (Coming in M1)

### What is Reddit?

Reddit is a social media platform. ORBIT will use Reddit API to collect posts from trading-related subreddits.

**Target subreddits:**
- r/stocks
- r/investing
- r/wallstreetbets

**Status**: 🚧 Integration in progress

---

### Get Reddit API Keys (Preparation)

1. **Create Reddit account**: https://www.reddit.com
2. **Create app**: https://www.reddit.com/prefs/apps
   - Click "Create App" or "Create Another App"
   - Select "script" type
   - Name: "ORBIT Research"
   - Redirect URI: `http://localhost:8080`
   - Click "Create app"

3. **Add to `.env`** (when M1 integration complete):

```bash
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_secret_here
REDDIT_USER_AGENT=ORBIT/1.0 by u/your_reddit_username
```

**Rate limits (free tier):**
- 60 requests per minute
- OAuth2 authentication required

---

## Runtime Configuration

Additional `.env` settings:

```bash
# Data directory (default: ./data)
ORBIT_DATA_DIR=/srv/orbit/data

# User-Agent for HTTP requests (required for Stooq, Reddit)
ORBIT_USER_AGENT=ORBIT/1.0

# Logging level: DEBUG, INFO, WARNING, ERROR
ORBIT_LOG_LEVEL=INFO
```

---

## Security Best Practices

### 1. Never Commit API Keys

```bash
# Verify .env is in .gitignore
cat .gitignore | grep .env

# Should output:
# .env
```

### 2. Use Environment-Specific Keys

```bash
# Development
.env.development

# Production
.env.production

# Load specific env:
cp .env.production .env
```

### 3. Rotate Keys Regularly

- Regenerate Alpaca keys every 3-6 months
- Regenerate Gemini keys if compromised
- Use separate keys for dev vs production

### 4. Restrict Key Permissions

- **Alpaca**: Use "Paper Trading" keys (not live trading)
- **Gemini**: Use project-specific keys (not personal account keys)

---

## Troubleshooting

### "API key not found" error

```bash
# Verify .env exists
ls -la .env

# Check .env is loaded
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('Alpaca key:', os.getenv('ALPACA_API_KEY'))
print('Gemini key:', os.getenv('GEMINI_API_KEY_1'))
"
```

### "Authentication failed" error

```bash
# Check for whitespace in keys (common issue)
cat .env | grep "ALPACA_API_KEY="

# Should NOT have spaces:
# ✓ ALPACA_API_KEY=PK123456
# ✗ ALPACA_API_KEY = PK123456
# ✗ ALPACA_API_KEY=PK123456

# Re-copy keys from provider dashboards
```

### "Rate limit exceeded" error

```bash
# Alpaca: Add more keys or slow down
# Check current rate:
grep "429" logs/ingestion_news_backfill_*.log

# Gemini: Wait for quota reset (00:00 PT) or add more keys
grep "quota" logs/gemini_*.log
```

---

## Quick Reference

**Minimal .env for M1:**

```bash
# Alpaca (news data)
ALPACA_API_KEY=your_websocket_key
ALPACA_API_SECRET=your_websocket_secret
ALPACA_API_KEY_1=your_rest_key
ALPACA_API_SECRET_1=your_rest_secret

# Gemini (sentiment)
GEMINI_API_KEY_1=your_gemini_key

# Runtime
ORBIT_DATA_DIR=./data
ORBIT_USER_AGENT=ORBIT/1.0
ORBIT_LOG_LEVEL=INFO
```

---

## Related Documentation

- [01_repository_setup.md](01_repository_setup.md) - Repository setup
- [02_cli_commands.md](02_cli_commands.md) - Command reference
- [04_historical_backfill.md](04_historical_backfill.md) - Multi-key backfill guide
- [env_keys.md](../03-config/env_keys.md) - Technical key specification
- [rate_limits.md](../04-data-sources/rate_limits.md) - Rate limit strategies
