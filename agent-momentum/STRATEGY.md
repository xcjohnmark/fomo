# MOMENTUM / QUICK FLIP STRATEGY

## Fomo Memecoin Research & Momentum Detection System

**Version:** 1.0  
**Primary platform:** Fomo  
**Purpose:** Identify short-term momentum setups that may offer favorable risk/reward for quick trades.

---

# 1. Strategy Overview

The Momentum / Quick Flip strategy attempts to identify memecoins experiencing **active and accelerating buying interest**.

The strategy does not attempt to predict which coin will eventually become a large project.

It asks a much narrower question:

> **"Is there enough current buying activity, price momentum, participation, liquidity, and trader interest to justify watching this coin for a potential short-term continuation?"**

The strategy operates on short time horizons.

The core idea is:

**Price movement + volume + buying pressure + participation + liquidity + trader activity + narrative = momentum setup**

No individual metric is sufficient.

A coin can have:

* enormous 24H gains but currently be collapsing;
* huge volume but mostly selling;
* many holders but no current momentum;
* high liquidity but no reason for the price to move;
* strong buying activity but extremely poor liquidity;
* an exciting narrative but no actual market participation.

Therefore, the system evaluates multiple dimensions simultaneously.

---

# 2. The Core Mental Model

The agent should think about the market using these relationships:

### Price = What is happening

Price movement tells us whether the token is currently moving.

### Volume = How much participation is behind the movement

A price increase accompanied by increasing volume is more meaningful than a price increase occurring on very little activity.

### Buys/Sells = Which side is more active

Buy and sell counts provide information about transaction activity.

### Buyers/Sellers = How broad the participation is

The number of unique buyers and sellers can reveal whether activity is broad or concentrated among a small number of traders.

### Liquidity = How tradable the movement is

Liquidity determines how easily a position can be entered and exited without excessive slippage.

### Holders = Whether participation is expanding

Increasing holder participation can indicate that the token is attracting new participants.

### Top 10% = Concentration risk

If a small number of wallets control a large portion of supply, those wallets can create substantial selling pressure.

### Trader activity = What active traders are doing

Trader activity can provide additional confirmation that experienced/active participants are paying attention to the token.

### Narrative = Why people might care

Narrative can explain why attention is entering the token.

Narrative should be treated as a **supporting factor**, not proof of momentum.

---

# 3. Required Coin Record

Every candidate analyzed by the system must produce a structured record.

## Market Data

```text
COIN:
Market Cap:
Price:

5M Change:
1H Change:
4H Change:
24H Change:

5M Volume:
1H Volume:
24H Volume:

Liquidity:

Buys:
Sells:

Buyers:
Sellers:

Holders:
Top 10 %:

Age:

Trader Activity:
Narrative:
```

For machine-readable research storage:

```text
timestamp
token
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
top10_percentage
age
trader_activity
narrative
momentum_score
alert_reason
```

Additional fields should eventually be added:

```text
scan_status
confirmation_status
entry_price
entry_timestamp
invalidation_price
target_price
exit_price
exit_timestamp
holding_time
return_percentage
max_favorable_excursion
max_adverse_excursion
exit_reason
```

---

# 4. INITIAL SCAN

The initial scan is designed to answer:

> **"Is this coin worth spending another 10–20 minutes studying?"**

The initial scan should be fast.

Do not spend 30–60 minutes analyzing every coin.

The process should be:

**Discover → Filter → Score → Watch → Confirm → Trade/Reject**

The initial scan should normally take approximately **1–3 minutes per candidate** once the trader becomes familiar with the interface.

---

# 5. INITIAL SCAN ORDER

The preferred order is:

1. Market Cap
2. Liquidity
3. 24H Volume
4. 5M Change
5. 1H Change
6. 4H Change
7. 24H Change
8. 5M/1H volume
9. Buys vs Sells
10. Buyers vs Sellers
11. Holders
12. Top 10%
13. Age
14. Trader Activity
15. Narrative

The first three establish whether the coin is even worth considering.

The next several determine whether momentum is currently occurring.

The final metrics help determine the quality and risk of the setup.

---

# 6. STEP 1 — MARKET CAP

### Question

> How large is this token currently?

Market cap provides context for the size of the token.

It should never be interpreted as the amount of money currently available to buy or sell the token.

### What to look for

The system should define a target market-cap range based on historical testing.

For example:

```text
Very small MC:
Potentially explosive but often extremely risky.

Moderate MC:
Potentially attractive for momentum trading.

Large MC:
Usually requires significantly more capital/attention to produce large percentage moves.
```

Do not automatically reject a coin because it is large or small.

Instead ask:

> "Given this market cap, is the current volume and buying activity large enough to produce meaningful movement?"

### Important relationship

Compare:

**Volume / Market Cap**

A $5M volume token with a $100K market cap is experiencing very different activity from a $5M volume token with a $500M market cap.

---

# 7. STEP 2 — LIQUIDITY

Liquidity measures how easily traders can enter and exit positions without causing excessive price impact.

### The key question

> "If I enter this trade, can I reasonably exit it?"

Higher liquidity does **not** automatically mean higher returns.

Instead:

> **Higher liquidity = greater trading capacity and generally better execution.**

Lower liquidity can produce explosive price movement but can also produce:

* large slippage;
* difficult exits;
* price manipulation;
* severe losses during panic selling.

### Liquidity-to-market-cap ratio

Calculate:

```text
Liquidity Ratio = Liquidity / Market Cap
```

This provides additional context.

Example:

```text
Market Cap = $200K
Liquidity = $100K

Liquidity Ratio = 50%
```

versus:

```text
Market Cap = $200K
Liquidity = $5K

Liquidity Ratio = 2.5%
```

The second token requires significantly more caution.

### Agent question

> "Is liquidity sufficient relative to the intended position size and current market activity?"

---

# 8. STEP 3 — 24H VOLUME

24H volume tells us how much trading activity has occurred over the previous 24 hours.

But:

> **High 24H volume does not mean current bullish momentum.**

A token could have generated enormous volume during a pump and now be collapsing.

Therefore, 24H volume is context.

The more important question is:

> "Is trading activity still occurring right now?"

This leads to the 5M and 1H measurements.

---

# 9. STEP 4 — SHORT-TERM PRICE MOMENTUM

The agent should compare:

```text
5M Change
1H Change
4H Change
24H Change
```

These timeframes should be interpreted together.

### Example A — Healthy continuation

```text
5M:  +4%
1H:  +15%
4H:  +35%
24H: +80%
```

This indicates positive movement across multiple timeframes.

Potential interpretation:

**Continuing/accelerating momentum.**

---

### Example B — Pump already reversing

```text
5M:  -12%
1H:  -25%
4H:  +180%
24H: +900%
```

The 24H number looks incredible.

But the current momentum is bearish.

Potential interpretation:

**Major reversal.**

This should not receive a strong momentum score simply because the 24H change is large.

---

### Example C — Early momentum

```text
5M:  +8%
1H:  +4%
4H:  -3%
24H: +10%
```

This could represent a new short-term breakout.

However, confirmation is required.

Potential interpretation:

**Early momentum / possible acceleration.**

---

# 10. STEP 5 — VOLUME MOMENTUM

Price movement should be evaluated alongside volume.

The agent should ask:

> "Is participation increasing as price moves?"

Ideally:

```text
Price ↑
Volume ↑
Buyers ↑
Buying activity ↑
```

This is stronger than:

```text
Price ↑
Volume ↓
Buyers stagnant
```

### Volume acceleration

Compare:

```text
5M Volume
1H Volume
24H Volume
```

The agent should not simply rank coins by absolute volume.

It should consider volume relative to the token's size.

Useful derived metrics:

```text
5M Volume / Market Cap
1H Volume / Market Cap
24H Volume / Market Cap
```

These help identify unusually active tokens.

---

# 11. STEP 6 — BUYS VS SELLS

Compare:

```text
Buys
Sells
```

A simple transaction imbalance:

```text
Buy Ratio = Buys / (Buys + Sells)
```

Example:

```text
Buys = 700
Sells = 300

Buy Ratio = 70%
```

This suggests more buy transactions than sell transactions.

However:

> **More buys does not automatically mean bullish momentum.**

One large seller can overwhelm hundreds of small buyers.

Therefore, transaction counts should be combined with volume.

---

# 12. STEP 7 — BUYERS VS SELLERS

Compare:

```text
Buyers
Sellers
```

This answers a slightly different question.

For example:

```text
1,000 buys
200 sellers
```

could mean repeated purchases by a small number of traders.

But:

```text
800 buyers
300 sellers
```

suggests broader participation.

The system should therefore consider:

### Transaction pressure

```text
Buys vs Sells
```

and:

### Participant breadth

```text
Buyers vs Sellers
```

Both are useful.

---

# 13. STEP 8 — HOLDERS

Holder count provides information about participation.

Potentially positive:

```text
Price ↑
Volume ↑
New buyers ↑
Holders ↑
```

This suggests participation may be broadening.

But holder count alone is not a momentum signal.

A token can have thousands of holders and no current momentum.

The agent should ask:

> "Is holder participation consistent with the current momentum?"

---

# 14. STEP 9 — TOP 10 HOLDER CONCENTRATION

Top 10 percentage measures how much supply is concentrated among the largest holders.

### Lower concentration

Generally means supply is more distributed.

### Higher concentration

Means fewer wallets control a larger percentage of supply.

This creates additional risk because large holders may be capable of creating significant selling pressure.

The agent should ask:

> "Could a small number of wallets materially disrupt this setup?"

Do not use one universal percentage as an automatic rejection threshold without testing it against historical data.

---

# 15. STEP 10 — AGE

Age tells us how mature the token is.

### Very young token

Potential advantages:

* rapid attention;
* explosive movement;
* early momentum.

Potential disadvantages:

* extreme volatility;
* limited historical data;
* higher manipulation risk;
* unstable liquidity.

### Older token

Potential advantages:

* more established liquidity;
* larger holder base;
* more historical behavior.

Potential disadvantages:

* momentum may already be exhausted;
* larger market cap may make explosive movement harder.

Age should therefore be treated as context.

---

# 16. STEP 11 — TRADER ACTIVITY

Trader activity is a confirmation/supporting signal.

The agent should ask:

> "Are active traders paying attention to this token?"

Look for:

* increasing trader activity;
* successful traders entering;
* multiple traders entering rather than one isolated wallet;
* trader activity occurring alongside increasing volume;
* trader activity occurring alongside positive price movement.

Trader activity should not be interpreted as:

> "Someone bought, therefore I should buy."

The agent must account for timing.

A trader who entered five minutes ago may already be profitable and preparing to exit.

Therefore:

**Trader activity = information, not an automatic trade signal.**

---

# 17. STEP 12 — NARRATIVE

Narrative answers:

> "Why is anyone paying attention to this token?"

Examples:

* current meme trend;
* viral event;
* celebrity/influencer attention;
* ecosystem trend;
* community activity;
* new platform attention;
* news/event-driven attention.

Narrative is a **supporting factor**.

The system must never say:

> "Strong narrative = buy."

Instead:

> "Strong narrative + increasing attention + increasing volume + positive momentum = stronger setup."

---

# 18. MOMENTUM SCORING SYSTEM

The initial scan produces a score from **0–100**.

The score represents:

> **How attractive is this coin for further momentum investigation?**

It does NOT represent:

> "Probability that the coin will go up."

It does NOT represent:

> "Buy this coin."

---

## Score Components

| Factor                 |  Points |
| ---------------------- | ------: |
| Market-cap suitability |       5 |
| Liquidity quality      |      15 |
| Volume activity        |      15 |
| Price momentum         |      20 |
| Buy/sell pressure      |      15 |
| Buyer/seller breadth   |      10 |
| Holder growth/quality  |       5 |
| Top-10 concentration   |       5 |
| Trader activity        |       5 |
| Narrative              |       5 |
| **Total**              | **100** |

---

# 19. MARKET-CAP SCORE — 0 TO 5

The system should eventually learn the optimal market-cap range from historical data.

Initial framework:

### 5 points

Market cap is within the historically favorable range for the strategy.

### 3–4 points

Reasonable but less ideal.

### 1–2 points

Very large or very small relative to the strategy's tested range.

### 0 points

Extreme conditions combined with poor liquidity or other major risks.

Market cap should never dominate the score.

---

# 20. LIQUIDITY SCORE — 0 TO 15

Evaluate:

1. Absolute liquidity.
2. Liquidity relative to market cap.
3. Liquidity relative to intended position size.
4. Whether liquidity appears stable.
5. Whether volume is disproportionately large relative to liquidity.

### 13–15

Strong liquidity relative to the token and intended trade.

### 9–12

Acceptable.

### 5–8

Caution.

### 0–4

Very thin liquidity or unacceptable execution risk.

---

# 21. VOLUME SCORE — 0 TO 15

Ask:

> Is there enough trading activity to support the movement?

### 13–15

Strong current volume with evidence of increasing activity.

### 9–12

Healthy activity.

### 5–8

Moderate or uncertain.

### 0–4

Low or deteriorating volume.

Volume should be compared with:

* market cap;
* liquidity;
* 5M activity;
* 1H activity;
* price movement.

---

# 22. PRICE MOMENTUM SCORE — 0 TO 20

This is the most important component.

### 17–20

Strong short-term momentum.

Characteristics:

* positive 5M;
* positive 1H;
* supportive 4H;
* price structure continuing;
* movement accompanied by volume.

### 13–16

Good momentum.

### 9–12

Mixed/early momentum.

### 5–8

Weak momentum.

### 0–4

Negative/reversing momentum.

A huge 24H gain must not compensate for severe current weakness.

---

# 23. BUY/SELL PRESSURE SCORE — 0 TO 15

Evaluate:

```text
Buys vs Sells
Buy volume vs Sell volume, if available
```

### 13–15

Strong and persistent buying pressure.

### 9–12

Moderately positive.

### 5–8

Balanced/mixed.

### 1–4

Selling pressure.

### 0

Strong selling dominance.

The system should prioritize **volume imbalance** over raw transaction count when both are available.

---

# 24. BUYER/SELLER BREADTH — 0 TO 10

### 8–10

Many buyers relative to sellers.

### 6–7

Moderately positive.

### 4–5

Balanced.

### 2–3

Seller-heavy.

### 0–1

Strongly seller-dominated.

Broad participation is generally stronger than a move driven by a few traders.

---

# 25. HOLDERS — 0 TO 5

### 5

Holder participation appears to be expanding alongside momentum.

### 3–4

Healthy holder base.

### 1–2

Limited participation or uncertain.

### 0

Holder structure creates substantial concern.

Absolute holder count should not be treated as universally good or bad.

---

# 26. TOP 10 CONCENTRATION — 0 TO 5

### 5

Healthy distribution.

### 3–4

Moderate concentration.

### 1–2

High concentration.

### 0

Extreme concentration or clear distribution risk.

Again, historical testing should eventually determine the exact thresholds.

---

# 27. TRADER ACTIVITY — 0 TO 5

### 5

Strong and increasing activity from relevant traders.

### 3–4

Positive activity.

### 1–2

Limited activity.

### 0

No meaningful confirmation or concerning activity.

---

# 28. NARRATIVE — 0 TO 5

### 5

Strong current narrative directly associated with increasing attention.

### 3–4

Relevant narrative.

### 1–2

Weak/unclear narrative.

### 0

No identifiable catalyst.

A strong narrative cannot override weak market data.

---

# 29. SCORE INTERPRETATION

### 85–100 — STRONG CANDIDATE

The token deserves immediate confirmation analysis.

This does NOT mean buy.

Action:

**WATCH / CONFIRM**

---

### 70–84 — WATCH

The token has several attractive characteristics but requires confirmation.

Action:

**WATCH 10–20 MIN**

---

### 55–69 — CONDITIONAL

There may be something interesting, but evidence is incomplete.

Action:

**WATCH ONLY IF A SPECIFIC CATALYST EXISTS**

---

### 40–54 — WEAK

Insufficient evidence.

Action:

**IGNORE**

---

### 0–39 — REJECT

Poor momentum setup or excessive risk.

Action:

**IGNORE**

---

# 30. CRITICAL RULE — SCORE IS NOT ENTRY SIGNAL

The score answers:

> **"Should I investigate this coin further?"**

The confirmation phase answers:

> **"Is the momentum actually continuing?"**

The entry phase answers:

> **"Is there a favorable entry point right now?"**

These are three separate decisions.

---

# 31. CONFIRMATION PHASE

Once a coin passes the initial scan, stop looking for reasons to buy.

Instead, look for evidence that the original momentum thesis is either **strengthening or failing**.

Observe the coin for approximately **10–20 minutes**, depending on volatility.

---

# 32. CONFIRMATION CHECKLIST

## A. Price Structure

Look for:

* higher highs;
* higher lows;
* continuation after pullbacks;
* successful reclaim of previous levels;
* controlled pullbacks.

Avoid:

* repeated lower highs;
* sharp breakdowns;
* immediate rejection;
* large unexplained drops.

---

## B. Volume

Positive:

```text
Price ↑
Volume remains strong/increases
```

Better:

```text
Pullback → volume decreases
Continuation → volume increases
```

This can indicate that selling pressure is weakening while buyers return.

Negative:

```text
Price ↑
Volume collapses
```

This can indicate weakening momentum.

---

## C. Buy/Sell Pressure

Watch whether buying pressure remains dominant.

Positive:

```text
Buyers > Sellers
Buys > Sells
Buy volume > Sell volume
```

Negative:

```text
Sellers increasing
Buyers decreasing
Sell volume increasing
```

---

## D. Participation

Monitor:

* new buyers;
* holders;
* traders;
* transaction activity.

A healthy setup should ideally attract additional participation.

---

## E. Liquidity

Ensure liquidity remains sufficient.

A sudden liquidity deterioration is a major warning.

---

## F. Trader Activity

Look for continued interest from active traders.

Do not chase a trader who has already made a large move.

---

# 33. CONFIRMATION STATES

Every candidate should be assigned one of these states.

### CONFIRMED

Momentum is continuing.

Characteristics:

* positive short-term price movement;
* healthy/increasing volume;
* buying pressure;
* broad participation;
* acceptable liquidity;
* no major invalidation signal.

---

### DEVELOPING

Potential setup, but confirmation is incomplete.

Wait.

---

### WEAKENING

Momentum is losing strength.

Examples:

* volume declining;
* buyers disappearing;
* sellers increasing;
* lower highs;
* failed breakout.

Do not enter simply because the token is still green.

---

### INVALIDATED

The original momentum thesis has failed.

Examples:

* major breakdown;
* severe selling pressure;
* liquidity problem;
* extreme rejection;
* major wallet/distribution concern.

Candidate is removed from active consideration.

---

# 34. ENTRY FRAMEWORK

An entry occurs only after:

**Initial Scan → High Score → Confirmation**

The entry should have four predefined components:

```text
Entry
Target
Invalidation
Time Limit
```

Before entering, the trader must be able to answer:

### Entry

> At what price/zone am I entering?

### Target

> Where will I take profit if momentum continues?

### Invalidation

> What event proves my momentum thesis is wrong?

### Time Limit

> If momentum does not develop within the expected period, when do I exit?

If these cannot be defined, the setup is incomplete.

---

# 35. HOLDING THE POSITION

The strategy does not use:

> "I bought, therefore I hold."

The correct rule is:

> **Hold while the original momentum thesis remains valid.**

During the trade continuously monitor:

* price;
* short-term momentum;
* volume;
* buying pressure;
* sellers;
* liquidity;
* trader activity.

The position should be reconsidered if the conditions that justified entry disappear.

---

# 36. EXIT CONDITIONS

There are four primary exit categories.

## 1. Target Exit

Price reaches the predefined target.

---

## 2. Momentum Exit

Momentum weakens materially.

Examples:

* lower highs;
* volume collapse;
* selling pressure increases;
* buyers disappear;
* failed continuation.

---

## 3. Invalidation Exit

The original thesis becomes false.

Example:

> Entry thesis = breakout continuation.

Then:

> Breakout fails + price breaks structure + sellers dominate.

The thesis is invalidated.

Exit.

---

## 4. Time Exit

The expected momentum does not occur within the predefined time window.

Example:

> Expected continuation within 30 minutes.

If 45–60 minutes pass and nothing happens, the trade may no longer represent the setup that was originally identified.

---

# 37. DO NOT MOVE THE INVALIDATION BECAUSE OF HOPE

A critical rule:

> **Never change the original thesis simply because the position is losing.**

The strategy is designed to trade momentum, not to turn failed momentum trades into long-term investments.

---

# 38. ALERT SYSTEM

The agent should notify the trader when a candidate reaches a predefined threshold.

Example:

```text
MOMENTUM ALERT

Token: XYZ

Market Cap: $180K
Liquidity: $42K

5M: +7.2%
1H: +18.4%
4H: +11.2%
24H: +45.8%

5M Volume: $14K
1H Volume: $91K
24H Volume: $420K

Buys/Sells: 182 / 97
Buyers/Sellers: 141 / 72

Holders: 1,842
Top 10: 18.4%

Age: 2h 14m

Trader Activity: Increasing
Narrative: AI/meme trend

Momentum Score: 88/100

Status: CONFIRMATION CANDIDATE

Reason:
Short-term price acceleration is occurring alongside increasing
volume and buyer dominance. Liquidity is acceptable relative to
current activity.

Next:
Observe for continuation for 10–20 minutes.
```

The agent should NOT say:

```text
BUY XYZ
```

It should say:

```text
MOMENTUM SETUP DETECTED
```

---

# 39. ALERT REASONS

The `alert_reason` field should explain **why** the coin triggered.

Examples:

```text
5M price acceleration + increasing volume + buyer dominance
```

```text
Early breakout with rising 5M volume and broad buyer participation
```

```text
Strong continuation after controlled pullback
```

```text
High short-term volume relative to market cap + positive buy imbalance
```

The explanation must be based on actual observed metrics.

Never fabricate a reason.

---

# 40. AGENT OPERATING PRINCIPLES

The agent must follow these rules.

### Rule 1 — Never invent missing data

If a value cannot be read:

```text
UNKNOWN
```

Do not estimate.

---

### Rule 2 — Separate FACTS from INTERPRETATION

Example:

```text
FACT:
5M Change = +8.2%

INTERPRETATION:
Short-term momentum is positive.
```

Never present interpretation as raw data.

---

### Rule 3 — Short timeframes matter more for quick flips

A coin with:

```text
24H = +500%
5M = -20%
1H = -35%
```

should not receive a strong current-momentum score.

---

### Rule 4 — Volume must be contextualized

High volume alone is not bullish.

Determine:

* when the volume occurred;
* whether it is increasing;
* whether buying or selling dominates;
* whether price is responding.

---

### Rule 5 — Liquidity is an execution constraint

Liquidity does not predict price direction.

It determines how safely the trader can participate.

---

### Rule 6 — Narrative is supporting evidence

Narrative cannot replace market confirmation.

---

### Rule 7 — Do not chase

If a coin has already experienced an extreme vertical move and short-term momentum is deteriorating, the agent should flag:

```text
EXTENDED / POSSIBLE REVERSAL
```

rather than automatically generating a bullish alert.

---

### Rule 8 — Avoid confirmation bias

The agent must actively search for evidence against the setup.

Every alert should contain:

```text
Why it looks good
AND
What could invalidate it
```

---

# 41. MOMENTUM SETUP CLASSIFICATION

The agent should classify candidates into:

### 1. EARLY MOMENTUM

Price has recently started accelerating.

Characteristics:

* positive 5M;
* positive 5M volume;
* improving buy pressure;
* 1H may still be relatively small.

Potential advantage:

Early entry.

Risk:

Momentum may fail quickly.

---

### 2. CONTINUATION

A previously established move is continuing.

Characteristics:

* positive 5M;
* positive 1H;
* healthy 4H;
* sustained volume;
* continued buying.

Potential advantage:

More confirmation.

Risk:

Entry may be later in the move.

---

### 3. BREAKOUT

Price breaks from a recent consolidation/range.

Ideal confirmation:

```text
Breakout
+
Volume expansion
+
Buyer dominance
+
Continued price acceptance
```

---

### 4. PULLBACK CONTINUATION

Price temporarily declines but does not destroy the bullish structure.

Ideal behavior:

```text
Initial move ↑
Pullback ↓
Selling volume decreases
Buyers return
Price resumes ↑
```

This can be preferable to chasing a vertical candle.

---

### 5. EXHAUSTION

The token has already experienced a very large move.

Characteristics:

* extreme 24H gain;
* declining short-term momentum;
* heavy selling;
* volume spikes without continued price progress.

Potential classification:

```text
HIGH RISK / POSSIBLE REVERSAL
```

---

# 42. SCENARIOS

## Scenario 1 — Strong Momentum Continuation

```text
5M: +5%
1H: +17%
4H: +35%
24H: +60%

Volume: increasing
Buys > Sells
Buyers > Sellers
Liquidity: healthy
```

Interpretation:

Strong candidate.

The move is positive across multiple timeframes and supported by participation.

Action:

**High-priority confirmation.**

---

# 43. Scenario 2 — Huge 24H Pump, Current Collapse

```text
24H: +700%
4H: +300%
1H: -25%
5M: -12%
```

Interpretation:

Historical momentum is strong, but current momentum is bearish.

Action:

**Do not score as a strong quick-flip momentum setup.**

Classification:

**Reversal / exhaustion.**

---

# 44. Scenario 3 — Price Rising but Volume Falling

```text
5M: +6%
1H: +15%

5M Volume: falling
Buyers: stagnant
Sellers: increasing
```

Interpretation:

Price is still rising, but participation is weakening.

Action:

**Developing/weakening.**

Wait for stronger confirmation.

---

# 45. Scenario 4 — Huge Volume but Sellers Dominate

```text
24H Volume: extremely high

Buys: 4,000
Sells: 4,500

Buy volume: $300K
Sell volume: $600K
```

Interpretation:

High activity does not equal bullish activity.

The market may be distributing.

Action:

**Reject or monitor for reversal.**

---

# 46. Scenario 5 — Low Liquidity Explosive Move

```text
Market Cap: $150K
Liquidity: $5K

5M: +18%
Volume: increasing
Buyers: increasing
```

Interpretation:

The momentum may be real, but execution risk is extremely high.

Action:

**High momentum / high execution risk.**

Do not let the momentum score hide the liquidity risk.

---

# 47. Scenario 6 — High Liquidity but No Momentum

```text
Market Cap: $20M
Liquidity: $3M

5M: +0.2%
1H: -0.4%
4H: +1%
Volume: stable
```

Interpretation:

Highly tradable but not necessarily a quick-flip opportunity.

Action:

**Reject for momentum strategy.**

Good liquidity does not create momentum.

---

# 48. Scenario 7 — Early Breakout

```text
5M: +9%
1H: +4%
4H: -2%
24H: +8%

5M volume suddenly increasing
Buyers increasing
```

Interpretation:

Potential early momentum.

The 4H trend is not yet strong, but the short-term change may represent the beginning of a new move.

Action:

**Watch closely for confirmation.**

Do not enter solely because the 5M candle is green.

---

# 49. Scenario 8 — Pullback With Healthy Structure

Initial move:

```text
+40%
```

Then:

```text
5M: -4%
```

But:

* selling volume declines;
* liquidity remains healthy;
* buyers return;
* price holds above the previous breakout area.

Interpretation:

Potential healthy pullback rather than trend failure.

Action:

**Wait for renewed buying confirmation.**

This can provide a better entry than chasing the original move.

---

# 50. Scenario 9 — High Buyer Count but Large Seller Volume

```text
Buyers: 1,500
Sellers: 500

But:

Buy volume: $100K
Sell volume: $500K
```

Interpretation:

Many small buyers are being overwhelmed by larger sellers.

This is an important nuance.

Action:

**Do not interpret buyer count alone as bullish.**

Volume matters.

---

# 51. Scenario 10 — Strong Narrative, Weak Market

Narrative:

```text
Extremely popular meme
```

But:

```text
5M: -5%
1H: -12%
Volume: declining
Sellers > Buyers
```

Interpretation:

The narrative exists, but the market is not currently rewarding it.

Action:

**Reject as a current momentum setup.**

Narrative is not momentum.

---

# 52. Scenario 11 — Strong Trader Activity but Late Entry

A successful trader enters.

Immediately afterward:

```text
Price +20%
```

Then:

```text
5M momentum slowing
Selling increasing
```

Interpretation:

The trader's activity was useful information, but entering after the move may create poor risk/reward.

Action:

**Do not chase.**

Wait for continuation or a controlled pullback.

---

# 53. Scenario 12 — Healthy Momentum but High Top-10 Concentration

```text
5M: +7%
1H: +22%
Volume: increasing
Buyers > Sellers
Liquidity: healthy

Top 10: 55%
```

Interpretation:

Momentum is strong, but concentration creates additional downside risk.

Action:

**Reduce confidence / require stronger confirmation.**

The setup is not automatically rejected, but concentration must be explicitly recognized.

---

# 54. Scenario 13 — Very Young Coin

```text
Age: 15 minutes
5M: +20%
Volume: rapidly increasing
Liquidity: moderate
Holders: rapidly increasing
```

Interpretation:

Potentially powerful early momentum.

But there is little historical information.

Action:

**High-volatility early setup.**

Require stronger liquidity and execution checks.

---

# 55. Scenario 14 — Mature Coin Suddenly Accelerates

```text
Age: 3 months
Market Cap: $2M

Previously:
5M: flat
1H: flat

Now:
5M: +8%
Volume: rapidly increasing
Buyers: rapidly increasing
```

Interpretation:

A mature token showing sudden renewed attention may be interesting because the movement represents a change in behavior.

Action:

**Investigate catalyst + confirm continuation.**

---

# 56. Scenario 15 — Everything Looks Good Except 5M Momentum

```text
MC: suitable
Liquidity: strong
Volume: strong
Holders: healthy
Top 10: healthy
Narrative: strong

5M: -1%
1H: +15%
4H: +30%
```

Interpretation:

This is not necessarily bad.

The coin may simply be consolidating.

Action:

**Watch for a 5M reversal/continuation signal.**

Do not automatically reject.

---

# 57. SCENARIO 16 — Strong Price Increase With Weak Participation

```text
5M: +10%
1H: +20%

But:
Volume: declining
Buyers: declining
Holders: flat
Trader activity: declining
```

Interpretation:

Price is increasing without improving participation.

Potentially late-stage movement.

Action:

**Require additional confirmation.**

---

# 58. SCENARIO 17 — Strong Setup Suddenly Invalidated

Initial setup:

```text
Momentum Score: 91
```

During confirmation:

```text
5M: +8% → -6%
Volume: falling
Sellers: increasing
Trader activity: declining
```

Interpretation:

The original setup has changed.

Action:

**Invalidate the alert.**

The original 91 score does not remain valid forever.

---

# 59. SCENARIO 18 — High Score but Bad Entry

A token scores:

```text
92/100
```

But the price has just moved:

```text
+25% in several minutes
```

and is now extremely extended.

Interpretation:

A good candidate can still have a bad entry.

The agent should distinguish:

**Good token/setup**

from:

**Good entry right now**

Action:

**Wait for continuation or controlled pullback.**

---

# 60. RESEARCH DATABASE

Every alert must be saved.

At minimum:

```text
timestamp
token
market_cap
price
5m_change
1h_change
4h_change
24h_change
liquidity
5m_volume
1h_volume
24h_volume
buys
sells
buyers
sellers
holders
top10_percentage
age
trader_activity
narrative
momentum_score
alert_reason
```

After the alert, the system should collect future observations.

For example:

```text
price_at_alert
price_5m
price_10m
price_20m
price_30m
price_60m
```

Then calculate:

```text
return_5m
return_10m
return_20m
return_30m
return_60m
```

Also record:

```text
maximum_gain_after_alert
maximum_loss_after_alert
```

---

# 61. MEASURING WHETHER THE STRATEGY ACTUALLY WORKS

The strategy should not be trusted simply because individual examples look good.

It must be tested.

For every alert calculate:

### Win rate

```text
Winning alerts / Total alerts
```

### Average winner

Average positive return.

### Average loser

Average negative return.

### Expectancy

```text
Expectancy =
(Win Rate × Average Win)
-
(Loss Rate × Average Loss)
```

### Maximum favorable excursion

How far the token moved in the favorable direction after the alert.

### Maximum adverse excursion

How far it moved against the setup.

### Optimal holding period

Determine whether the strategy performs best after:

```text
5 minutes
10 minutes
20 minutes
30 minutes
60 minutes
```

Do not assume the optimal holding period.

**Measure it.**

---

# 62. AGENT LEARNING LOOP

The research process should continuously improve the scanner.

```text
SCAN
 ↓
SCORE
 ↓
ALERT
 ↓
OBSERVE
 ↓
RECORD OUTCOME
 ↓
ANALYZE
 ↓
IDENTIFY WHICH CONDITIONS WORK
 ↓
UPDATE THRESHOLDS
 ↓
SCAN AGAIN
```

Eventually the agent should discover patterns such as:

> "Coins with X market cap, Y liquidity ratio, Z 5M volume acceleration, and A buy imbalance historically performed best over 20 minutes."

This is where the user's data-science background becomes particularly useful.

---

# 63. DO NOT OPTIMIZE TOO EARLY

Do not immediately create dozens of complicated rules.

Start with:

```text
Market Cap
Liquidity
Volume
Price Momentum
Buys/Sells
Buyers/Sellers
Holders
Top 10
Age
Trader Activity
Narrative
```

Collect data.

Then determine which factors actually predict favorable short-term outcomes.

The strategy should eventually become **data-driven rather than based on arbitrary thresholds.**

---

# 64. FINAL AGENT DECISION TREE

The agent should conceptually operate like this:

```text
TOKEN DISCOVERED
       ↓
Is market cap suitable?
       ↓
Is liquidity acceptable?
       ↓
Is volume meaningful?
       ↓
Is short-term momentum positive?
       ↓
Is volume supporting the movement?
       ↓
Are buyers stronger than sellers?
       ↓
Is participation broad?
       ↓
Is holder/distribution structure acceptable?
       ↓
Is trader activity supportive?
       ↓
Is there a relevant narrative/catalyst?
       ↓
CALCULATE MOMENTUM SCORE
       ↓
Score ≥ 85?
       ↓
HIGH-PRIORITY CONFIRMATION
       ↓
Observe 10–20 minutes
       ↓
Is price continuing?
       ↓
Is volume continuing?
       ↓
Is buying pressure continuing?
       ↓
Is participation continuing?
       ↓
Is liquidity still acceptable?
       ↓
CONFIRMED SETUP
       ↓
Define:
Entry
Target
Invalidation
Time Limit
       ↓
ENTRY DECISION
       ↓
MONITOR
       ↓
Target / Momentum Failure / Invalidation / Time Exit
       ↓
RECORD RESULT
       ↓
UPDATE RESEARCH DATABASE
```

---

# 65. THE MOST IMPORTANT QUESTIONS

For every coin, the agent should ultimately answer these questions:

### 1. Is the coin moving?

Look at:

```text
5M
1H
4H
24H
```

### 2. Is the movement happening now?

Prioritize short-term data over old 24H performance.

### 3. Is there enough activity behind the movement?

Look at:

```text
5M volume
1H volume
24H volume
```

### 4. Are buyers actually participating?

Look at:

```text
Buys
Sells
Buyers
Sellers
Buy volume
Sell volume
```

### 5. Can I realistically trade it?

Look at:

```text
Liquidity
Liquidity / Market Cap
```

### 6. Is participation broadening?

Look at:

```text
Holders
Buyers
Trader activity
```

### 7. Can large holders disrupt the trade?

Look at:

```text
Top 10%
```

### 8. Why is attention entering?

Look at:

```text
Narrative
Trader activity
```

### 9. Is this early, continuing, or already exhausted?

Compare all timeframes.

### 10. What would prove the setup wrong?

Define invalidation before entry.

---

# 66. FINAL STRATEGY PRINCIPLE

The strategy is not:

> "Find a coin that will 2x."

It is:

> **"Find a coin where current buying pressure, price acceleration, trading activity, participation, liquidity, and trader interest are aligned strongly enough to justify a short-term momentum trade."**

The system should therefore prioritize **alignment**.

A strong setup looks like:

```text
Positive short-term price movement
+
Increasing volume
+
Buying pressure
+
Broad buyer participation
+
Acceptable liquidity
+
Healthy distribution
+
Increasing trader activity
+
Relevant narrative
```

The more of these factors that align, the stronger the candidate.

But even a perfect-looking setup can fail.

Therefore:

> **Scan → Score → Confirm → Define risk → Enter → Monitor → Exit → Record → Learn**

That loop is the actual strategy.

---

# 67. AGENT OUTPUT STANDARD

For every high-quality candidate, the agent should produce:

```text
========================================
MOMENTUM SETUP DETECTED
========================================

COIN:
AGE:

MARKET:
MC:
PRICE:
LIQUIDITY:

MOMENTUM:
5M:
1H:
4H:
24H:

VOLUME:
5M:
1H:
24H:

FLOW:
BUYS:
SELLS:
BUYERS:
SELLERS:

PARTICIPATION:
HOLDERS:
TOP 10%:

TRADER ACTIVITY:
NARRATIVE:

MOMENTUM SCORE:
XX/100

CLASSIFICATION:
Early / Continuation / Breakout / Pullback / Exhaustion

STATUS:
Watch / Confirmation / Confirmed / Weakening / Invalidated

WHY:
[2–4 objective reasons]

RISKS:
[2–4 objective risks]

CONFIRMATION NEEDED:
[What must happen next]

INVALIDATION:
[What would make the setup fail]

NEXT ACTION:
Ignore / Watch / Continue Confirmation

========================================
```

The agent must never hide risk behind the score.

A **90/100** candidate with a major liquidity or concentration risk must explicitly show that risk.

The objective is not to produce more alerts.

The objective is to produce **fewer, higher-quality momentum setups whose characteristics can be measured and improved over time.**
