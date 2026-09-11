# Pump.fun Momentum / Quick Flip Intelligence Agent

## 0. What We Are Building

The system is a **real-time momentum research and alerting agent for Pump.fun tokens**.

It is NOT initially:

* an auto-trader
* a bot that automatically buys tokens
* a bot that automatically publishes Pump callouts
* an LLM that randomly decides which coins are good
* a "100x coin predictor"

It IS:

> A systematic engine that continuously monitors Pump.fun-compatible market data, identifies short-term momentum setups according to the Momentum / Quick Flip strategy in STRATEGY.md, generates a defined trade plan, sends the setup to Telegram, records the call in a database, monitors what happens afterward, and automatically determines whether the setup succeeded or failed.

The ultimate objective is to build a statistically validated trading strategy.

---

# 1. The Strategy the Agent Must Implement

## Core philosophy

The strategy does not ask:

> "Will this coin moon?"

It asks:

> "Is there enough current buying pressure and participation to justify a short-term momentum trade?"

The strategy is designed for **quick flips**, not long-term holding.

The basic trade structure is:

**Entry → Target → Invalidation → Time Limit**

Every opportunity must have all four.

---

# 2. Required Market Data

The system should attempt to collect:

```text
timestamp
chain
token_ca
symbol
name

market_cap
price

5m_change
1h_change
4h_change
24h_change

5m_volume
1h_volume
24h_volume

liquidity

buys
sells
buyers
sellers

holders
holder_growth
top10_percentage

token_age

trader_activity
wallet_activity

pool_address
pool/platform

narrative
```

Important:

**token_ca + chain is the canonical token identity.**

Ticker/symbol is NOT sufficient.

The same token may trade through multiple pools, so the system must also track:

```text
pool_address
```

when available.

---

# 3. What Each Metric Means

## Price

Tells us what the market is currently doing.

Price increasing alone is insufficient.

## Volume

Tells us how much participation exists.

Increasing volume alongside increasing price is more interesting than price increasing while volume disappears.

## Buy/Sell activity

Measures directional pressure.

We care about:

```text
buys > sells
buy volume > sell volume
buyers > sellers
```

But one metric should never be considered independently.

## Liquidity

Liquidity is primarily an **execution constraint**.

Higher liquidity generally means:

* easier entry
* easier exit
* lower slippage
* greater position capacity

Lower liquidity can produce explosive moves but creates much greater execution and exit risk.

The strategy therefore does NOT simply reward the highest liquidity.

## Holder growth

We want to know whether participation is broadening.

## Top-10 concentration

High concentration increases the possibility that a small number of holders can create significant selling pressure.

## Trader activity

We want to know whether experienced/active wallets are participating.

This is supporting evidence, not a blind copy-trading signal.

## Narrative

Narrative is a supporting catalyst.

It is NOT sufficient by itself.

---

# 4. Initial Momentum Score

Version 1 should use deterministic scoring.

Total = 100.

```text
Market-cap suitability       5
Liquidity quality           15
Volume activity              15
Price momentum               20
Buy/sell pressure            15
Buyer/seller breadth         10
Holder quality/growth         5
Top-10 concentration          5
Trader activity               5
Narrative                     5
                              ---
                             100
```

Interpretation:

```text
85–100  Strong candidate
70–84   Watch
55–69   Conditional
40–54   Weak
0–39    Reject
```

IMPORTANT:

The score is NOT automatically a buy signal.

It answers:

> "Is this setup worth investigating?"

---

# 5. Momentum Confirmation

A high score must be followed by confirmation.

The system should classify a setup as:

```text
CONFIRMED
DEVELOPING
WEAKENING
INVALIDATED
```

Confirmation looks for:

* higher highs
* higher lows
* continued volume
* increasing volume acceleration
* buyer dominance
* increasing participation
* healthy liquidity
* continuing trader activity

Warning signs:

* price reversal
* volume collapse
* seller dominance
* declining buyers
* price increasing without participation
* liquidity deterioration
* distribution
* sudden large-wallet selling

---

# 6. The Quick Flip Model

Every confirmed opportunity must produce:

```text
Entry Zone
Target Zone
Invalidation
Expected Holding Time
```

Example:

```text
Current MC: $180K

Entry:
$175K–$190K MC

Target:
$300K–$350K MC

Invalidation:
$160K MC

Expected holding:
15–60 minutes
```

Do NOT force every trade to target 2x.

A target should be based on:

* current structure
* volatility
* momentum
* liquidity
* recent price movement
* resistance/extension
* historical performance of similar setups

The strategy can have a 2x target when justified, but:

> "Target +100% if momentum continues"

is preferable to:

> "This will 2x."

---

# 7. Phase 1 — Project Foundation

## Your tasks

You personally should:

1. Create the project folder.
2. Create a GitHub repository.
3. Create your Telegram bot using BotFather.
4. Get the Telegram bot token.
5. Create the Telegram chat/group/channel where alerts will arrive.
6. Obtain the chat ID.
7. Create the database.
8. Obtain legitimate market-data/API/RPC credentials where required.
9. Never put secrets directly into source code.
10. Create `.env`.

Example:

```text
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

DATABASE_URL=

SOLANA_RPC_URL=

DATA_PROVIDER_API_KEY=
```

Do not give the coding agent your secrets inside prompts.

---

## Coding-agent prompt

```text
You are the lead software engineer for a research-grade crypto market intelligence project.

Build the initial project foundation for a Python 3.12+ application.

Project goal:
Build a real-time Pump.fun Momentum / Quick Flip research and alerting system.

The system will eventually:
1. collect legitimate market data,
2. normalize token data,
3. calculate deterministic momentum scores,
4. detect Quick Flip setups,
5. send Telegram alerts,
6. store every alert,
7. monitor the outcome of every alert,
8. determine whether each call was profitable or invalidated,
9. produce research statistics,
10. eventually support statistical/ML optimization.

Do NOT build an auto-trader.

Do NOT implement automatic Pump.fun callout publishing.

Create a clean production-oriented Python project.

Use:
- Python 3.12+
- PostgreSQL
- SQLAlchemy
- Pydantic
- asyncio
- python-telegram-bot
- pandas/numpy where appropriate
- pytest
- dotenv/environment configuration

Create:
- app/
- config/
- database/
- models/
- services/
- strategy/
- telegram/
- collectors/
- tests/
- scripts/

Create configuration management using environment variables.

Create database connection infrastructure.

Create logging.

Create a health-check mechanism.

Create README documentation.

Do not overengineer the project.

Do not add Redis, Celery, Kubernetes, microservices or a frontend at this stage.

The architecture must allow future replacement of the data provider without rewriting the strategy engine.

Before writing significant code, inspect the repository and propose the architecture. Then implement it.

```

---

# 8. Phase 2 — Data Source Research and Adapter

This is one of the most important phases.

DO NOT immediately build the strategy.

First establish:

> What legitimate source can provide the data required by the strategy?

The preferred architecture is:

```text
Pump/Solana-compatible data
        ↓
Data Adapter
        ↓
Normalized TokenSnapshot
        ↓
Database
```

The strategy must never depend directly on a specific API response format.

Create an internal schema:

```python
TokenSnapshot
```

with the standardized fields.

The external provider becomes an adapter.

Example:

```text
Provider A
    ↓
ProviderAAdapter
    ↓
TokenSnapshot

Provider B
    ↓
ProviderBAdapter
    ↓
TokenSnapshot
```

This allows us to replace providers later.

---

## Coding-agent prompt

```text
Implement the market-data abstraction layer.

Research the currently available legitimate Pump.fun/Solana data-access options before implementing the collector.

Do not scrape Pump.fun webpages.

Do not use unauthorized browser automation.

Do not rely on reverse-engineered private endpoints for production.

Prefer official Pump developer/protocol resources, Solana RPC/indexing infrastructure, and legitimate market-data providers.

Determine which required fields are available from each source:

- token CA/mint
- chain
- pool
- price
- market cap
- liquidity
- 5m change
- 1h change
- 4h change
- 24h change
- 5m volume
- 1h volume
- 24h volume
- buys
- sells
- buyers
- sellers
- holders
- top-10 concentration
- token age
- trader/wallet activity

Create a DATA_SOURCE_MATRIX.md documenting:

field
provider
availability
timestamp quality
definition
limitations
cost
rate limits
terms/usage restrictions

Then create a provider abstraction.

Create:

MarketDataProvider

and:

TokenSnapshot

The strategy must only consume TokenSnapshot objects.

Do not implement trading.

Do not implement callout publishing.

Write unit tests for normalization and missing-data handling.

If a field is unavailable, represent it as unavailable.

NEVER invent or estimate missing data.
```

---

# 9. Phase 3 — Automated Data Collector

Now collect snapshots automatically.

Start small.

Do not scan every token on the platform immediately.

First prove that:

```text
token discovery
→ data collection
→ storage
```

works reliably.

Store timestamped snapshots.

Example:

```text
14:00:00
ABC
MC = $180K
Price = ...
Liquidity = ...
5m change = ...

14:01:00
ABC
MC = $184K
...
```

This historical data becomes extremely valuable later.

---

## Coding-agent prompt

```text
Build the automated market-data collector.

Requirements:

1. Discover eligible tokens using the selected legitimate data source.
2. Normalize every token into TokenSnapshot.
3. Store timestamped snapshots in PostgreSQL.
4. Deduplicate identical observations where appropriate.
5. Preserve timestamps from the provider.
6. Store provider name and provider version/source.
7. Store chain, token CA and pool address.
8. Handle API failures gracefully.
9. Handle rate limits.
10. Retry transient failures.
11. Never fabricate missing values.
12. Log collection failures.

Create database tables for:

tokens
pools
market_snapshots
data_sources

The collector must be independently runnable from the strategy engine.

Add tests.

Create a command that performs a small controlled collection run.

Do not yet send Telegram alerts.
```

---

# 10. Phase 4 — Build the Momentum Engine

Now implement the strategy exactly as defined.

This must be **deterministic Python**, not an LLM.

Input:

```text
TokenSnapshot history
```

Output:

```text
MomentumAnalysis
```

Containing:

```text
score
score_breakdown
setup_state
reasons
warnings
```

The LLM does NOT determine the score.

---

## Coding-agent prompt

```text
Implement the Momentum / Quick Flip strategy engine.

The strategy is designed for short-term momentum trades.

It must evaluate:

- market-cap suitability
- liquidity
- volume activity
- price momentum
- buy/sell pressure
- buyer/seller breadth
- holder growth
- top-10 concentration
- trader activity
- narrative

Total score = 100.

Weights:

market-cap suitability = 5
liquidity = 15
volume = 15
price momentum = 20
buy/sell pressure = 15
buyer/seller breadth = 10
holder quality/growth = 5
top-10 concentration = 5
trader activity = 5
narrative = 5

Classify:

85–100 = STRONG
70–84 = WATCH
55–69 = CONDITIONAL
40–54 = WEAK
0–39 = REJECT

Do NOT treat score as a buy signal.

Implement confirmation states:

CONFIRMED
DEVELOPING
WEAKENING
INVALIDATED

Require multi-metric agreement.

Examples:

Strong current price momentum + accelerating volume + buyer dominance =
stronger setup.

Huge 24h gain + collapsing 5m/1h momentum =
reversal/exhaustion warning.

High volume + seller dominance =
not automatically bullish.

Low liquidity + explosive price movement =
high execution risk.

High liquidity + no momentum =
not a Quick Flip setup.

Strong narrative + weak market data =
not sufficient.

Strong trader activity + late price extension =
do not chase.

High top-10 concentration =
risk adjustment.

Young token =
require stronger liquidity/execution confirmation.

Price rising while participation weakens =
warning.

Never chase a token merely because it has already moved substantially.

Every decision must be explainable through its individual feature scores.

Write extensive unit tests covering the 18 strategy scenarios defined in the project specification.

Do not use an LLM for numerical scoring.
Make use of the STRATEGY.md file to understand the strategy.
```

---

# 11. Phase 5 — Entry / Target / Invalidation Engine

Now turn a setup into an actual **trade plan**.

The engine should calculate:

```text
entry_zone
target_zone
invalidation
expected_holding_period
```

Do not blindly use:

```text
target = entry × 2
```

Instead create a target-selection module.

Initially it can use deterministic rules.

Later it can learn from historical data.

---

## Coding-agent prompt

```text
Build the Quick Flip trade-plan engine.

Input:
MomentumAnalysis
TokenSnapshot history

Output:

QuickFlipPlan:
- entry_price
- entry_market_cap
- entry_zone
- target_price
- target_market_cap
- target_percentage
- invalidation_price
- invalidation_market_cap
- expected_holding_minutes
- risk_flags
- plan_reason

Rules:

1. Entry must be based on the current setup, not an arbitrary number.
2. If the token has already moved too far from the initial setup, classify it as EXTENDED rather than chasing.
3. Target should be based on market structure, momentum, volatility and historical behavior when sufficient data exists.
4. Invalidation must represent a genuine breakdown of the thesis.
5. Expected holding period must remain short-term.
6. Never guarantee that the target will be reached.
7. If there is insufficient data to construct a reasonable plan, return NO_PLAN.
8. Never invent missing market information.

Create tests for:
- normal setup
- extended setup
- weak setup
- invalidated setup
- insufficient data
- high-volatility setup
- low-liquidity setup
```

---

# 12. Phase 6 — Telegram Bot

Now connect the strategy to Telegram.

The bot should be your primary interface.

No website is required.

Suggested commands:

```text
/start
/status
/scan
/watch
/unwatch
/history
/stats
/paper
/settings
```

The system can also send automatic alerts.

---

# 13. Telegram Notification Format

This should become your recognizable format.

```text
⚡ QUICK FLIP SETUP

$ABC
CA: 7x...abc

Momentum Score: 88/100
Status: CONFIRMED

MC: $180K
Liquidity: $35K
5M: +8.4%
1H: +24%
4H: +31%

Volume: ACCELERATING
Buyers/Sellers: 214 / 137
Buys/Sells: 318 / 201

ENTRY ZONE
$175K–$190K MC

TARGET
$300K–$350K MC
Potential: +58% to +100%

INVALIDATION
Below $160K MC

EXPECTED HOLD
15–60 min

WHY
• 5M momentum accelerating
• Volume expanding
• Buyers dominating sellers
• Liquidity acceptable
• Participation increasing

RISKS
• High short-term volatility
• Top-holder concentration: 28%
• Setup becomes weaker if volume collapses

PLAN
Quick momentum flip.
Not a long-term hold.
If momentum breaks, the setup is invalidated.
```

The language should **not** say:

> "100x gem."

It should not say:

> "Guaranteed 2x."

It should not manufacture certainty.

---

## Coding-agent prompt

```text
Build the Telegram notification layer.

Use python-telegram-bot.

Create:

/start
/status
/scan
/watch
/unwatch
/history
/stats
/paper
/settings

Implement automatic opportunity alerts.

Use the following notification format:

⚡ QUICK FLIP SETUP

$TOKEN

CA:
Momentum Score:
Status:

MC:
Liquidity:
5M:
1H:
4H:

Volume:
Buyers/Sellers:
Buys/Sells:

ENTRY ZONE:
TARGET:
INVALIDATION:
EXPECTED HOLD:

WHY:
- reason
- reason
- reason

RISKS:
- risk
- risk

PLAN:
Quick momentum flip.
Not a long-term hold.
If momentum breaks, the setup is invalidated.

Never write:
"guaranteed"
"100x"
"free money"
"will moon"
or equivalent certainty claims.

The Telegram layer must only display information produced by the strategy engine.

Do not allow the LLM to modify numerical values.

Add buttons where useful:
View Token
Watch
Paper Trade
Ignore

Do not implement automatic Pump.fun callout publishing.
```

---

# 14. Phase 7 — Call Recording

THIS IS CRITICAL.

Every alert becomes a permanent research observation.

Database table:

```text
strategy_calls
```

Fields:

```text
call_id

timestamp
token_ca
chain
pool_address

symbol

strategy_version

momentum_score

entry_price
entry_market_cap

entry_zone_low
entry_zone_high

target_price
target_market_cap

invalidation_price
invalidation_market_cap

expected_holding_minutes

setup_state

reasons
risk_flags
```

Then outcome fields:

```text
outcome_status

actual_peak_price
actual_peak_market_cap

actual_low_price
actual_exit_price

time_to_target
time_to_invalidation

max_favorable_excursion
max_adverse_excursion

return_percentage

holding_time

exit_reason

result
```

---

# 15. Phase 8 — Automatic Outcome Monitor

This is where the project becomes much more powerful.

Once a call is created:

```text
CALL
 ↓
MONITOR
 ↓
TARGET HIT?
INVALIDATION HIT?
TIME LIMIT?
 ↓
RESOLVE
```

For every call, the monitor continues collecting data.

Possible results:

```text
TARGET_HIT
INVALIDATED
TIME_EXIT
EXPIRED
NO_EXECUTION
DATA_ERROR
```

Do NOT rewrite history.

If the token went to +150% after your alert but first hit invalidation, the result must reflect the predefined rules.

No hindsight.

---

## Coding-agent prompt

```text
Build the Call Outcome Monitor.

Every generated Quick Flip setup must become an immutable strategy call.

After a call is created, continuously monitor the token.

Determine:

1. Did the target get reached?
2. Did invalidation get reached?
3. How long did each take?
4. What was the maximum favorable excursion?
5. What was the maximum adverse excursion?
6. Did the setup expire because the time limit was reached?

The original entry, target, invalidation and expected duration must NEVER be modified after the call is created.

Resolve each call according to predefined rules.

Store:

actual_peak_price
actual_peak_market_cap
actual_low_price
actual_exit_price
time_to_target
time_to_invalidation
holding_time
return_percentage
max_favorable_excursion
max_adverse_excursion
exit_reason
result

Do not use future information to modify the original call.

The purpose is to create a clean research dataset without hindsight bias.

Write tests for target-first, invalidation-first and timeout scenarios.
```

---

# 16. Phase 9 — Paper Trading

Before real money:

```text
Alert
 ↓
Paper Trade
 ↓
Simulated entry
 ↓
Monitor
 ↓
Simulated exit
 ↓
Performance
```

The Telegram alert should have:

**PAPER TRADE**

When you press it:

```text
paper_entry_timestamp
paper_entry_price
paper_entry_MC
```

is recorded.

This gives you a simulated track record.

---

# 17. Phase 10 — The Research Database

After enough calls, your database becomes the most valuable asset.

Every call contains:

```text
What did we see?
What did the strategy predict?
What actually happened?
```

You should eventually have hundreds/thousands of observations.

Example:

```text
CALL 001
Score 91
MC $120K
Liquidity $25K
5M +12%
Volume accelerating
Target +80%
Result WIN

CALL 002
Score 87
MC $210K
Liquidity $18K
5M +15%
Volume accelerating
Target +100%
Result LOSS

...
```

---

# 18. Phase 11 — Strategy Analytics

Build:

```text
/stats
```

The system should calculate:

### Core metrics

```text
Number of calls
Win rate
Loss rate

Average winner
Average loser

Median winner
Median loser

Expectancy

Average holding time
Median holding time

Target-hit rate
Invalidation rate
Timeout rate

Maximum favorable excursion
Maximum adverse excursion

Maximum drawdown
```

Expectancy:

```text
(win rate × average win)
-
(loss rate × average loss)
```

Also break results down by:

```text
market cap
liquidity
volume
5m momentum
1h momentum
token age
top-10 concentration
buyer/seller ratio
buy/sell ratio
time of day
day of week
market conditions
strategy score
```

---

# 19. Phase 12 — Find Out What Actually Matters

This is where your data-science background becomes useful.

We may discover:

```text
Score 85–90:
62% success

Score 90–95:
71% success

Score 95–100:
68% success
```

Or:

```text
Liquidity < $10K:
poor performance

Liquidity $20K–$50K:
best performance

Liquidity > $100K:
lower volatility but fewer opportunities
```

Or:

```text
5M momentum + volume acceleration
is highly predictive.

Narrative alone
is almost useless.
```

The strategy should then evolve based on evidence.

---

# 20. Phase 13 — Strategy Versioning

NEVER overwrite the old strategy.

Use:

```text
Momentum v1.0
Momentum v1.1
Momentum v1.2
Momentum v2.0
```

Every call records:

```text
strategy_version
```

This allows you to say:

```text
v1.0:
63% win rate

v1.1:
68%

v1.2:
71%
```

You can then determine whether changes actually improved the strategy.

---

# 21. Phase 14 — Statistical Optimization

Only AFTER sufficient data.

Do not immediately throw XGBoost at the problem.

First perform:

* correlation analysis
* feature distributions
* win/loss comparisons
* conditional probabilities
* feature importance
* threshold analysis
* walk-forward testing

For example:

> Among setups with score > 85, liquidity > $25K and accelerating 5M volume, what percentage reach +50% within 30 minutes?

That is much more useful than generic ML initially.

---

# 22. Phase 15 — ML Probability Model

Once there are enough observations:

```text
Historical calls
       ↓
Features
       ↓
Target outcome
       ↓
Train model
       ↓
Probability
```

Possible target:

```text
P(target reached before invalidation)
```

For example:

```text
Probability = 0.71
```

The model should NOT directly say:

> BUY.

Instead:

```text
Strategy rules:
CONFIRMED

Historical model:
71% probability of reaching target

Historical sample:
143 similar setups
```

This preserves the distinction between:

**strategy detection**

and

**statistical estimation**.

---

# 23. Phase 16 — The LLM Analyst

The LLM comes AFTER the deterministic engine.

Architecture:

```text
Market Data
     ↓
Strategy Engine
     ↓
Trade Plan
     ↓
LLM
     ↓
Explanation
     ↓
Telegram
```

The LLM should explain:

* why the setup qualifies
* important risks
* what changed
* whether the setup is weakening
* what confirmation means

It must NOT:

* invent numbers
* modify targets
* modify invalidation
* override the score
* hallucinate market data
* turn weak setups into buys

---

## LLM prompt

```text
You are the explanation layer for a deterministic Momentum / Quick Flip trading research system.

You do not decide whether a token qualifies.

The strategy engine has already made that determination.

Your job is to explain the supplied data clearly.

Rules:

1. Never invent data.
2. Never modify numerical values.
3. Never create a target that was not supplied.
4. Never create an invalidation that was not supplied.
5. Never claim certainty.
6. Never say the token will moon.
7. Never describe a setup as guaranteed.
8. Distinguish facts from interpretation.
9. Mention important risks.
10. Explain why the setup qualifies.
11. If the setup is weakening, say so.
12. If data is missing, explicitly state that it is missing.
13. This is a short-term momentum/Quick Flip strategy, not a long-term investment strategy.

Input:
- Token data
- Momentum score
- Score breakdown
- Confirmation state
- Entry zone
- Target
- Invalidation
- Expected holding time
- Risk flags

Output:
1. One-sentence thesis.
2. 3–5 reasons.
3. Key risks.
4. Short action-plan description.

Do not provide unsupported financial predictions.
```

---

# 24. Phase 17 — Fomo Validation

Only after the Pump.fun version works.

Remember the original problem:

> Can our external data reproduce the information we see on Fomo?

We use:

```text
chain + token CA
```

as the primary identity.

But also compare:

```text
pool
timestamp
price
liquidity
volume
buys
sells
buyers
sellers
```

The goal isn't necessarily:

> "Every number must be identical."

The goal is:

> "Does our data produce the same useful momentum signal?"

Eventually compare:

```text
Fomo signal
vs
Our signal
```

and calculate signal agreement.

This can tell us whether the Pump-based data infrastructure is representative enough for your original Fomo strategy.

---

# 25. Phase 18 — Manual Pump Callout Workflow

Because the Callout ecosystem has restrictions around automated callouts and artificial engagement, **you remain the publisher**.

The agent sends you:

```text
⚡ QUICK FLIP READY

$ABC

Entry:
$175K–$190K MC

Target:
$300K–$350K MC

Invalidation:
$160K MC

Expected hold:
15–60 min

Why:
...
```

You review it.

Then YOU manually create the Pump callout if you choose to.

Your callout should be factual and transparent.

Do not:

* coordinate buying
* promise returns
* fake engagement
* create multiple accounts
* manipulate activity
* hide compensation
* misrepresent your position
* use the system to manufacture activity

Pump's current Callout Terms specifically prohibit manipulation, fake engagement, automated callout/engagement activity intended to inflate rewards, and pump-and-dump behavior.

Also remember that Pump says Callout rewards are discretionary and can be zero, so treat them as a potential side benefit rather than guaranteed income.

---

# 26. Your Manual Quick Flip Callout Format

Use something consistent:

```text
⚡ QUICK FLIP

$ABC

MC: $180K
Liquidity: $35K

5M: +8.4%
1H: +24%

Momentum: 88/100

ENTRY:
$175K–$190K MC

TARGET:
$300K–$350K MC

INVALIDATION:
<$160K MC

EXPECTED HOLD:
15–60 min

THESIS:
Volume is accelerating alongside price,
with buyer participation currently exceeding
seller participation.

This is a short-term momentum setup,
not a long-term hold.

If momentum breaks, the setup is invalidated.
```

That makes your identity very different from:

> "BUY THIS GEM BEFORE IT MOONS."

Your positioning is:

**Quick Flip / Momentum Research**

---

# 27. Phase 19 — Track Your Public Callout Performance

There are now TWO datasets.

## Dataset A — Agent calls

Every opportunity detected by the system.

## Dataset B — Published callouts

Only opportunities you actually decided to publish.

This distinction matters.

You can eventually discover:

```text
Agent calls:
500

Published:
180

Successful:
112
```

Then compare:

```text
Agent accuracy
vs
Human-selected accuracy
```

You may discover that your manual filtering improves the system.

Or you may discover that your manual decisions make it worse.

That is valuable information.

---

# 28. Phase 20 — Build Your Track Record

Eventually your statistics can look like:

```text
QUICK FLIP TRACK RECORD

Calls analyzed: 427

Target hit: 281
Invalidated: 103
Timeout: 43

Target-hit rate: 65.8%

Median holding time: 27 min

Average winner: +71%
Average loser: -17%

Best-performing MC:
$100K–$300K

Best signal:
5M momentum + volume acceleration
+ buyer dominance
```

Only publish statistics based on the actual immutable dataset.

Never cherry-pick only successful calls.

---

# 29. Phase 21 — Risk and Capital Layer

Only after the strategy has a meaningful paper track record should real capital be considered.

The system should eventually calculate:

```text
Suggested maximum position
```

based on:

* liquidity
* expected slippage
* strategy confidence
* invalidation distance
* account risk limits

But do NOT build automatic execution initially.

Your first real-money version should still be:

```text
Agent
 ↓
Alert
 ↓
You decide
 ↓
Manual trade
 ↓
Agent records result
```

The system's job is to prove that the strategy works before automating execution.

---

# 30. Phase 22 — Production Deployment

Once everything works locally:

```text
GitHub
 ↓
Docker
 ↓
VPS/cloud server
 ↓
PostgreSQL
 ↓
Collector
 ↓
Strategy engine
 ↓
Telegram
```

The system should run continuously.

You should be able to restart it without losing state.

Implement:

* health checks
* structured logs
* error alerts
* database backups
* API rate-limit handling
* reconnect logic
* monitoring
* strategy version tracking

---

# 31. Final Architecture

The finished system should look like this:

```text
                    DATA SOURCES
                         │
              ┌──────────┴──────────┐
              │                     │
        Pump/Solana             Other Data
        market data              provider
              │                     │
              └──────────┬──────────┘
                         ↓
                  DATA ADAPTER
                         ↓
                 NORMALIZED DATA
                         ↓
                    DATABASE
                         ↓
                FEATURE ENGINEERING
                         ↓
                MOMENTUM ENGINE
                         ↓
              ┌──────────┴──────────┐
              │                     │
           REJECT                QUALIFY
                                  │
                                  ↓
                         CONFIRMATION ENGINE
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                INVALID                     CONFIRMED
                                                │
                                                ↓
                                       QUICK FLIP PLAN
                                                │
                                  Entry / Target / Invalidation
                                                │
                                                ↓
                                           LLM ANALYST
                                                │
                                                ↓
                                           TELEGRAM
                                                │
                              ┌─────────────────┼────────────────┐
                              │                 │                │
                          You review       Paper trade      Watch
                              │
                              ↓
                       Manual callout
                              │
                              ↓
                     OUTCOME MONITOR
                              │
                              ↓
                         CALL RESULT
                              │
                              ↓
                      RESEARCH DATABASE
                              │
                              ↓
                       /stats + analysis
                              │
                              ↓
                    STRATEGY IMPROVEMENT
                              │
                              ↓
                       New strategy version
```

# 32. The Correct Build Order

Do NOT build everything simultaneously.

Build in this exact order:

```text
PHASE 1
Project foundation

↓

PHASE 2
Data-source research

↓

PHASE 3
Data collector

↓

PHASE 4
Database + historical snapshots

↓

PHASE 5
Momentum scoring

↓

PHASE 6
Confirmation engine

↓

PHASE 7
Entry/target/invalidation engine

↓

PHASE 8
Telegram alerts

↓

PHASE 9
Call recording

↓

PHASE 10
Outcome monitoring

↓

PHASE 11
Paper trading

↓

PHASE 12
Statistics

↓

PHASE 13
Strategy optimization

↓

PHASE 14
ML probability model

↓

PHASE 15
LLM explanation layer

↓

PHASE 16
Fomo validation

↓

PHASE 17
Production deployment

↓

PHASE 18
Manual Pump callout workflow

↓

PHASE 19+
Only later consider more automation
```

# 33. Things You Must Personally Do

The coding agent cannot do these for you:

### Accounts

* Create Telegram bot
* Create Telegram chat/channel
* Get Telegram chat ID
* Create GitHub repository
* Create database account/server
* Obtain legitimate API/RPC credentials
* Create Pump account
* Complete any required platform eligibility/verification
* Secure your wallets
* Review the applicable Pump terms for your jurisdiction

### Strategy decisions

You must decide:

* minimum liquidity
* acceptable market-cap range
* maximum top-holder concentration
* maximum acceptable extension before entry
* preferred target ranges
* invalidation methodology
* maximum holding period
* which setups you personally consider publishable
* when a setup is too risky

The agent should implement these decisions, not invent them.

### Trading/callout decisions

Initially:

**YOU decide whether to trade.**

**YOU decide whether to publish a Pump callout.**

The system supplies the research.

---

# 34. Things the Coding Agent Should Do

The coding agent should handle:

* application architecture
* database schema
* API integration
* data normalization
* data collection
* feature calculations
* momentum scoring
* confirmation
* trade-plan calculation
* Telegram integration
* alert formatting
* call recording
* outcome monitoring
* paper trading
* statistics
* tests
* logging
* deployment configuration
* research scripts
* backtesting
* strategy-version tracking

---

# 35. The Most Important Rule for the Coding Agent

Give your coding agent this permanent instruction:

```text
This project is a research-first Momentum / Quick Flip intelligence system.

Never optimize for producing more alerts.

Optimize for producing HIGH-QUALITY, MEASURABLE, REPRODUCIBLE signals.

Every signal must be backed by timestamped data.

Every signal must have:
- entry
- target
- invalidation
- expected holding period
- strategy version

Every signal must be stored.

Every signal must be monitored afterward.

Never rewrite historical calls.

Never use future information to influence a past call.

Never fabricate missing data.

Never let an LLM override deterministic numerical strategy logic.

Never automatically trade.

Never automatically publish Pump callouts.

Never manipulate engagement, trading activity, rankings or reward systems.

The objective is to determine whether the Momentum / Quick Flip strategy actually has positive expectancy through empirical data.
```

# 36. The End Goal

The finished system should eventually let you wake up and have Telegram show:

```text
⚡ QUICK FLIP SETUP

$ABC

Momentum: 91/100
Status: CONFIRMED

MC: $182K
Liquidity: $34K

5M: +9.1%
1H: +27%
4H: +41%

Volume: ACCELERATING
Buyers/Sellers: 238/151

ENTRY:
$175K–$190K MC

TARGET:
$320K–$360K MC

INVALIDATION:
$162K MC

EXPECTED HOLD:
20–50 min

HISTORICAL MATCHES:
127

TARGET-HIT RATE:
69%

THESIS:
Price momentum, volume acceleration and
buyer participation are currently aligned.

RISKS:
High volatility.
Short-term setup.
Top-10 concentration elevated.

⚠️ Not a guaranteed outcome.
```

Then, regardless of what happens, the system records it.

If it wins:

```text
CALL #481 → TARGET HIT
+87%
34 minutes
```

If it loses:

```text
CALL #482 → INVALIDATED
-12%
11 minutes
```

If nothing happens:

```text
CALL #483 → TIMEOUT
+3%
60 minutes
```

After hundreds of these, you stop asking:

> **"Does my strategy sound good?"**

and start answering:

> **"Under exactly which conditions does my strategy work?"**

That is the real objective of this project.

**Build the data collection and measurement system first. The trading strategy is the hypothesis; the database is the experiment.**
