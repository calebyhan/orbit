# ORBIT

**Observational Reasoning & Behavior-Integrated Trading**

A machine learning system for predicting overnight price movements in equity markets using multi-modal data sources.

## Overview

ORBIT is a quantitative trading research platform that combines multiple signals to predict overnight gap movements in US equity markets. The system focuses on predicting close-to-open returns for SPY/VOO (S&P 500 ETFs).

**Key Features:**
- Multi-modal prediction (multi-head)
- Walk-forward validation with strict temporal discipline
- Production-ready pipeline for daily scoring and execution
- Comprehensive backtesting and regime analysis tools

## Project Status

**Current Phase:** Production deployment (backtest_v1 model validated)

- ✅ Data ingestion pipeline
- ✅ Feature engineering and model training
- ✅ Backtesting framework with regime analysis
- ✅ Out-of-sample validation (Nov 2024 - Nov 2025)
- ✅ Paper trading infrastructure
- 🚧 Live trading deployment (in progress)

## Research Results

**backtest_v1 Model (Nov 2024 - Nov 2025 out-of-sample):**
- Return: +76.49% (long-only overnight strategy)
- Sharpe Ratio: 6.09
- Max Drawdown: -3.25%
- Win Rate: 99.4% (157/158 trades)
- Regime-tested: Robust across bull/bear/high-vol/low-vol conditions

## Disclaimer

This software is for **research and educational purposes only**.

- Not financial advice or investment recommendations
- Past performance does not guarantee future results
- Trading involves substantial risk of loss
- Only trade with capital you can afford to lose
- Consult a licensed financial advisor before trading

The authors make no warranties about the accuracy, completeness, or reliability of this software. Use at your own risk.

## License

See [LICENSE](LICENSE) for details.

## Contact

For questions or collaboration: [issues](https://github.com/calebyhan/orbit/issues)

---

**Note**: This is a research project. The system is under active development and results should be validated in paper trading before any live deployment.
