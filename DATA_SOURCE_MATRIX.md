# DATA SOURCE MATRIX

## Legitimate Market Data Provider Evaluation for Pump.fun & Solana Memecoins

This document evaluates legitimate, terms-compliant, non-scraping data sources to establish the data availability foundation for the Momentum / Quick Flip strategy.

Per Strategy Rule 1: **Never invent or estimate missing data.** If a provider does not supply a metric, it is represented as `None` (`UNAVAILABLE`).

---

## 1. Provider Overview

| Provider | Access Type | Primary Strengths | Primary Gaps | Cost / Tier | Rate Limits | Terms & Restrictions |
|:---|:---|:---|:---|:---|:---|:---|
| **DexScreener** | Public REST API | Free, zero API key required, reliable real-time DEX liquidity, 5M/1H/24H price changes and volume, buy/sell transaction counts. | No 4H change (provides 6H instead), no unique wallet buyer/seller counts, no holder count or top-10 concentration. | Free ($0) | 300 requests/minute for token/pair endpoints. | Permitted for automated backend querying; no abusive polling or scraping. |
| **Birdeye** | Developer & Institutional REST API | Dedicated Solana DeFi metrics: exact holder counts, top 10 holder concentration %, 5M/1H/4H/24H price & volume, smart trader tracking. | Free tier has strict monthly Compute Unit (CU) limits; paid plans required for high-frequency daemon scanning. | Freemium (Free tier: 100K CU/mo; Paid from ~$250/mo). | 150–300 requests/second depending on endpoint & tier. | Backend usage only; API key must remain confidential. |
| **Solana JSON-RPC / Helius** | Official RPC & Enhanced Solana APIs | Authoritative on-chain source of truth. Direct SPL token largest accounts (`getTokenLargestAccounts`), token supply, real-time bonding curve state. | Does not pre-calculate rolling historical time-series changes (5M, 1H, 4H, 24H) without an external indexing database. | Freemium (Free tier: 100K credits/day, 50 req/s; Developer plans from $49/mo). | 50–200 req/s on free/dev tiers; Yellowstone gRPC available. | Permitted for all developer bot/indexing workloads. Commercial terms apply. |
| **GeckoTerminal (CoinGecko)** | Public REST API | Broad pool discovery across DEXs, pool reserves, 5M/1H/24H OHLCV. | No 4H change (only 6H), no holder distribution or wallet profiling, low rate limits on public tier. | Free ($0) / Paid CoinGecko API plans. | 30 requests/minute on public free tier. | Attribution required for public applications; strict 30 req/min throttling. |

---

## 2. Field-by-Field Availability Matrix

| Required Strategy Field | DexScreener API | Birdeye DeFi API | Solana RPC / Helius | GeckoTerminal API | Strategy Handling When Unavailable |
|:---|:---|:---|:---|:---|:---|
| **token CA / mint** | ✅ Available (`baseToken.address`) | ✅ Available (`address`) | ✅ Available (`mint`) | ✅ Available (`base_token_id`) | Mandatory identifier. Reject if missing. |
| **chain** | ✅ Available (`chainId: "solana"`) | ✅ Available (`chain: "solana"`) | ✅ Available (`solana`) | ✅ Available (`solana`) | Default to "solana". |
| **pool address** | ✅ Available (`pairAddress`) | ✅ Available (`mainPair`) | ✅ Available (bonding curve PDA / AMM pool) | ✅ Available (`pool_id`) | Preserved as string or `None`. |
| **price (USD)** | ✅ Available (`priceUsd`) | ✅ Available (`value` in `/price`) | ✅ Derived (bonding curve virtual reserves) | ✅ Available (`base_token_price_usd`) | Current market price. |
| **market cap (USD)** | ✅ Available (`marketCap` / `fdv`) | ✅ Available (`marketCap` / `mc`) | ✅ Derived (`supply * price`) | ✅ Available (`market_cap_usd` / `fdv_usd`) | Market cap in USD. |
| **liquidity (USD)** | ✅ Available (`liquidity.usd`) | ✅ Available (`liquidity`) | ✅ Derived (virtual SOL pool reserves) | ✅ Available (`reserve_in_usd`) | Pool liquidity. If `< MIN_LIQUIDITY_USD`, candidate filtered. |
| **5m change (%)** | ✅ Available (`priceChange.m5`) | ✅ Available (`priceChange5mPercent`) | ❌ Unavailable natively | ✅ Available (`price_change_percentage.m5`) | Price momentum score component. |
| **1h change (%)** | ✅ Available (`priceChange.h1`) | ✅ Available (`priceChange1hPercent`) | ❌ Unavailable natively | ✅ Available (`price_change_percentage.h1`) | Price momentum score component. |
| **4h change (%)** | ❌ Unavailable (provides `h6`) | ✅ Available (`priceChange4hPercent`) | ❌ Unavailable natively | ❌ Unavailable (provides `h6`) | **Represented as `None`**. Scorer handles absence neutrally without inventing data. |
| **24h change (%)** | ✅ Available (`priceChange.h24`) | ✅ Available (`priceChange24hPercent`) | ❌ Unavailable natively | ✅ Available (`price_change_percentage.h24`) | Historical context metric. |
| **5m volume (USD)** | ✅ Available (`volume.m5`) | ✅ Available (`volume5mUSD`) | ❌ Unavailable natively | ✅ Available (`volume_usd.m5`) | Volume acceleration metric. |
| **1h volume (USD)** | ✅ Available (`volume.h1`) | ✅ Available (`volume1hUSD`) | ❌ Unavailable natively | ✅ Available (`volume_usd.h1`) | Volume activity score component. |
| **24h volume (USD)** | ✅ Available (`volume.h24`) | ✅ Available (`volume24hUSD`) | ❌ Unavailable natively | ✅ Available (`volume_usd.h24`) | 24H volume context. |
| **buys (tx count)** | ✅ Available (`txns.m5.buys` / `h1.buys`) | ✅ Available (`buy5m` / `buy1h`) | ⚠️ Partial (requires parsing block logs) | ✅ Available (`transactions.m5.buys`) | Flow pressure metric. |
| **sells (tx count)** | ✅ Available (`txns.m5.sells` / `h1.sells`) | ✅ Available (`sell5m` / `sell1h`) | ⚠️ Partial (requires parsing block logs) | ✅ Available (`transactions.m5.sells`) | Flow pressure metric. |
| **buyers (unique wallets)**| ❌ Unavailable | ✅ Available (Trade history aggregation) | ✅ Available (Parsed enhanced transactions) | ❌ Unavailable | **Represented as `None`**. Scorer flags breadth as `UNKNOWN`. |
| **sellers (unique wallets)**| ❌ Unavailable | ✅ Available (Trade history aggregation) | ✅ Available (Parsed enhanced transactions) | ❌ Unavailable | **Represented as `None`**. Scorer flags breadth as `UNKNOWN`. |
| **holders (total count)** | ❌ Unavailable | ✅ Available (`holder` in `/token_security`) | ⚠️ Partial (paginated `getTokenAccounts`) | ❌ Unavailable | **Represented as `None`** unless enriched via Birdeye or RPC. |
| **top-10 concentration (%)**| ❌ Unavailable | ✅ Available (`top10UserPercent`) | ✅ Available (via `getTokenLargestAccounts`) | ❌ Unavailable | **Represented as `None`** unless enriched via Birdeye or RPC `getTokenLargestAccounts`. |
| **token age** | ✅ Available (`pairCreatedAt` timestamp)| ✅ Available (`creationTime`) | ✅ Available (block time of mint transaction) | ⚠️ Partial (pool creation time) | Converted to `age_seconds` and formatted string. |
| **trader / wallet activity** | ❌ Unavailable | ✅ Available (`/tokens/top_traders`) | ✅ Available (wallet address parsing) | ❌ Unavailable | **Represented as `None`** or "UNKNOWN" unless enriched. |

---

## 3. Data Quality & Timestamp Definitions

1. **Snapshot Timestamp (`timestamp`)**:
   - Quality: UTC ISO-8601 (`YYYY-MM-DDTHH:MM:SSZ`).
   - Definition: The exact moment the adapter captured and normalized the external response.
2. **Price & Liquidity Timestamps**:
   - Quality: Real-time spot (0–5 seconds latency on DEX pools).
   - Definition: Spot price calculated against the active bonding curve / Raydium pool quote reserves.
3. **Rolling Interval Metrics (5M, 1H, 24H)**:
   - Quality: Rolling window aggregation calculated by the indexing node.
   - Definition: Percentage price movement and cumulative volume within the trailing interval prior to query execution.
4. **Token Age**:
   - Quality: Authoritative Unix epoch milliseconds or seconds from pool initialization or mint event.

---

## 4. Recommended Production Architecture: The Composite Provider

Because no single free provider supplies 100% of the metrics:
1. **Primary Feed (Market Micro-Structure)**:
   - **DexScreener API** provides free, highly reliable price, volume (5m, 1h, 24h), price changes (5m, 1h, 24h), and buy/sell transaction counts.
2. **On-Chain Enrichment Feed (Holder Distribution & Security)**:
   - **Solana JSON-RPC (`getTokenLargestAccounts`) / Helius** provides exact top-10 concentration % and supply data with zero risk of vendor lock-in.
3. **`CompositeMarketDataProvider`**:
   - Combines the primary market feed with the on-chain enrichment provider to return a unified, rich `TokenSnapshot`.
   - If enrichment fails or is rate-limited, the system falls back gracefully: missing metrics are set to `None`, and the strategy evaluates only the confirmed data without inventing values.
