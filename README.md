# Fomo Pump.fun Momentum / Quick Flip Research & Alerting System

A research-grade market intelligence and alerting platform for Pump.fun and Solana memecoins, built strictly according to the [Momentum / Quick Flip Strategy](agent-momentum/STRATEGY.md).

The system continuously scans token pools, normalizes market micro-structure data, evaluates a **100-point deterministic momentum scoring rubric**, classifies setup structure, broadcasts structured Telegram notifications, persists every alert snapshot to a PostgreSQL/SQLite database, and tracks post-alert price observations (5m, 10m, 20m, 30m, 60m) to measure strategy expectancy and support future ML/statistical optimization.

---

## Key Design Principles

1. **Research & Intelligence, Not Auto-Trading**:
   - The engine produces high-conviction candidate alerts and tracks setup outcomes.
   - It does **not** execute automated swaps or auto-publish unverified callouts.
2. **Provider Agnostic (Decoupled Architecture)**:
   - Data collection is isolated behind the `BaseCollector` interface.
   - Real-time providers (Pump.fun WebSocket/APIs, DexScreener, Birdeye, Shyft, Helius, Geckoterminal, or custom RPCs) can be swapped in without modifying any strategy or alerting logic.
3. **Deterministic 100-Point Scoring Engine**:
   - Scores candidates across 10 dimensions: Market Cap, Liquidity, Volume, Price Momentum, Buy/Sell Pressure, Buyer/Seller Breadth, Holders, Top 10 Concentration, Smart Trader Activity, and Narrative.
4. **Outcome Tracking & Expectancy**:
   - Automatically tracks Maximum Favorable Excursion (MFE), Maximum Adverse Excursion (MAE), and win/loss performance at fixed intervals (5m, 10m, 20m, 30m, 60m) to discover optimal holding periods.

---

## Project Structure

```text
fomo/
├── app/
│   ├── __init__.py
│   ├── main.py                # Main async entry point and graceful shutdown handler
│   ├── health.py              # Health check service (DB, collector, Telegram)
│   └── logging.py             # Structured console and file logging
├── config/
│   ├── __init__.py
│   └── settings.py            # Pydantic Settings configuration (.env loading)
├── database/
│   ├── __init__.py
│   ├── base.py                # DeclarativeBase and TimestampMixin
│   └── session.py             # Async engine and session factory (PostgreSQL & SQLite)
├── models/
│   ├── __init__.py
│   ├── domain.py              # Pydantic domain models (NormalizedTokenData, ScoreBreakdown, etc.)
│   └── db.py                  # SQLAlchemy ORM models (TokenAlert, PriceObservation, SetupOutcome)
├── collectors/
│   ├── __init__.py
│   ├── base.py                # Abstract BaseCollector provider interface
│   └── mock_pump_collector.py # Reference collector simulating realistic market feeds
├── strategy/
│   ├── __init__.py
│   ├── scoring.py             # 100-point deterministic momentum scoring engine
│   ├── classifier.py          # Setup classifier & objective reason/risk extractor
│   └── engine.py              # Strategy evaluator filtering for score >= 85
├── telegram/
│   ├── __init__.py
│   ├── client.py              # Telegram client wrapper with dry-run support
│   └── formatter.py           # Standard Section 67 alert message formatter
├── services/
│   ├── __init__.py
│   ├── alert_recorder.py      # Database persistence service for alerts
│   ├── outcome_tracker.py     # Post-alert price tracking and performance metrics
│   └── scanner.py             # Market scanning loop coordinator
├── scripts/
│   ├── __init__.py
│   ├── init_db.py             # Database table creation script
│   └── run_scanner.py         # Direct CLI runner
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # Async test fixtures and sample token models
│   ├── test_classifier.py     # Classification and reason/risk tests
│   ├── test_collector_contract.py # Data provider contract verification
│   ├── test_health.py         # Subsystem health verification tests
│   ├── test_scanner_service.py# End-to-end scanner pipeline integration tests
│   └── test_scoring.py        # 100-point rubric boundary tests
├── agent-momentum/
│   └── STRATEGY.md            # Canonical strategy specification document
├── .env.example               # Environment variables template
├── .gitignore                 # Standard Python gitignore
├── pyproject.toml             # Build and dependency configuration
├── requirements.txt           # Pip dependencies
└── README.md                  # System documentation
```

---

## 100-Point Scoring Rubric Summary

| Dimension | Points | Description |
|:---|---:|:---|
| **Market-Cap Suitability** | 5 | Evaluates token size relative to tested sweet-spots ($50k–$5M). |
| **Liquidity Quality** | 15 | Assesses pool liquidity and the Liquidity-to-MC ratio. |
| **Volume Activity** | 15 | Measures short-term volume relative to market cap and acceleration. |
| **Price Momentum** | 20 | Evaluates 5M/1H/4H alignment. Strictly penalizes collapsing pumps. |
| **Buy/Sell Pressure** | 15 | Analyzes buy volume / transaction flow imbalance. |
| **Buyer/Seller Breadth**| 10 | Unique buyer wallet dominance over unique seller wallets. |
| **Holder Participation**| 5 | Holder expansion consistent with current momentum. |
| **Top 10 Concentration**| 5 | Penalizes supply concentration risk (>35%). |
| **Trader Activity** | 5 | Confirms activity by active/smart participants. |
| **Narrative Catalyst** | 5 | Supporting catalyst (meme, viral event, AI trend). |
| **Total** | **100** | Candidate triggers alert when **Score ≥ 85**. |

---

## Setup & Quickstart

### 1. Requirements
- Python 3.12+
- (Optional) PostgreSQL 14+ (SQLite is supported out-of-the-box for local testing)

### 2. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/xcjohnmark/fomo.git
cd fomo
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configuration
Copy the environment template:
```bash
cp .env.example .env
```
Edit `.env` to configure your database and Telegram credentials:
```ini
# PostgreSQL (Production): postgresql+asyncpg://postgres:password@localhost:5432/fomo_research
# SQLite (Local Dev/Testing):
DATABASE_URL=sqlite+aiosqlite:///./fomo_research.db

# Telegram Alerts (Leave empty to run in console Dry-Run mode):
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Strategy Thresholds:
MIN_MOMENTUM_SCORE=85
MIN_LIQUIDITY_USD=5000
SCAN_INTERVAL_SECONDS=10
```

### 4. Initialize Database
Create all tables:
```bash
python scripts/init_db.py
```

### 5. Check System Health
Verify connectivity to database, collector, and Telegram services:
```bash
python -m app.main --health
```

### 6. Run Scanner
- **Single scan pass (test run)**:
  ```bash
  python -m app.main --once
  ```
- **Continuous daemon loop**:
  ```bash
  python -m app.main
  ```

---

## Running Tests

The test suite runs with in-memory SQLite and mock feeds, requiring zero external infrastructure:
```bash
pytest -v
```

---

## Sample Alert Format (Section 67 Standard)

```text
========================================
🚨 MOMENTUM SETUP DETECTED
========================================

COIN: $XYZ
MINT: XYZpump11111111111111111111111111111111111
AGE: 2h 14m

MARKET:
MC: $180,000
PRICE: $0.00018000
LIQUIDITY: $42,000 (23.3%)

MOMENTUM:
5M: +7.2%
1H: +18.4%
4H: +11.2%
24H: +45.8%

VOLUME:
5M: $14,000
1H: $91,000
24H: $420,000

FLOW:
BUYS: 182
SELLS: 97
BUYERS: 141
SELLERS: 72

PARTICIPATION:
HOLDERS: 1,842
TOP 10%: 18.4%

TRADER ACTIVITY: Increasing smart trader volume
NARRATIVE: AI meme trend breakout

MOMENTUM SCORE: 94/100

CLASSIFICATION:
Breakout

STATUS:
Confirmation Candidate

WHY:
• Positive price alignment across short timeframes (5M: +7.2%, 1H: +18.4%)
• Broad participant breadth with 141 buyers vs 72 sellers (66.2% buyer ratio)
• Strong buy transaction dominance (182 buys vs 97 sells, 65.2%)
• Healthy liquidity backing ($42,000, 23.3% of MC)

RISKS:
• Execution risk: volatile memecoin momentum prone to abrupt reversal
• Short holding window: setup invalidates if 5M continuation stalls

CONFIRMATION NEEDED:
Higher highs on 5M timeframe accompanied by sustained or increasing buy volume

INVALIDATION:
Sharp 5M volume collapse or drop below support ($0.000162)

NEXT ACTION:
Watch 10-20 min / Verify volume continuation
========================================
```

---

## Extending the Data Provider

To connect a live Pump.fun or DEX feed, create a new class in `collectors/` inheriting from `BaseCollector`:

```python
from collectors.base import BaseCollector
from models.domain import NormalizedTokenData

class LivePumpFunCollector(BaseCollector):
    async def get_active_tokens(self) -> list[NormalizedTokenData]:
        # 1. Fetch raw payloads from Pump.fun WebSocket / REST API
        # 2. Map and normalize into NormalizedTokenData
        # 3. Return clean snapshots
        ...

    async def get_token_snapshot(self, token_address: str) -> NormalizedTokenData | None:
        ...

    async def get_current_price(self, token_address: str) -> float | None:
        ...

    async def health_check(self) -> bool:
        ...
```

Then simply inject your `LivePumpFunCollector()` in `app/main.py`. The strategy, classification, Telegram alerting, and research database continue operating without modification.
