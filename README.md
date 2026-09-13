# Fabric Market Pulse

Real-time cryptocurrency market analytics on Microsoft Fabric — tracking
Bitcoin, Ethereum, and Solana, with a live dashboard and automated alerts.

## Problem Statement

Cryptocurrency markets move fast — prices, trading volumes, and volatility
can shift significantly within seconds. Traders and analysts need to detect
these movements and react in near real-time, but building a system that can
*ingest*, *process*, *analyze*, and *alert on* such fast-moving data
traditionally requires stitching together several disconnected tools: a
message broker, a stream-processing engine, a time-series database, a BI
tool, and a separate alerting service — each provisioned, connected, secured,
and maintained independently.

**Microsoft Fabric** solves this with one unified, governed platform
(OneLake): real-time ingestion (Eventstream), low-latency querying
(Eventhouse/KQL), a lakehouse for historical analytics (Medallion
architecture), visualization (Power BI), and event-driven alerting
(Activator) — so the whole pipeline, from a live Binance feed to an email on
a 2% price move, runs in one workspace with no code required for the
streaming and alerting layers.

## Architecture

The pipeline follows standard Big Data / Streaming architecture patterns:

- **Ingestion Layer** — a Python producer (`ingestion/binance_to_fabric.py`)
  holds a WebSocket connection to Binance and pushes JSON payloads into
  Fabric Eventstream via its Kafka-compatible (Event Hubs) endpoint.
- **Real-Time Analytics Layer** — Fabric Eventhouse ingests ticks into a KQL
  table for low-latency querying, price-change calculations, and OHLC
  aggregation (`kql/`).
- **Automated Alerting Layer** — Fabric Activator watches the stream/KQL
  table and triggers email notifications on defined conditions
  (`activator/alert-rules-notes.md`).
- **Lakehouse (Medallion architecture)** — a single scheduled notebook
  (`notebooks/nb_market_transform.ipynb`) runs all stages end-to-end:
  - **Bronze** — `raw_market_ticks`, landed directly by Eventstream
  - **Silver** — `silver_market_ticks`, deduplicated and typed
  - **Gold** — `ohlc_1min` (1-minute candles) and `features_market_1min`
    (rolling SMAs, volatility, volume ratio), plus an in-notebook
    educational SMA-crossover backtest
- **Visualization** — a two-page Power BI report (`Fabric_Market_Pulse.pbix`)
  covering Historical Price Analysis and Volume Analysis.

```text
Binance (WebSocket)
   ↓
ingestion/binance_to_fabric.py
   ↓
Eventstream (custom endpoint source, Kafka protocol)
   ↓
Eventhouse / KQL — MarketData table
   ↓
   ├── notebooks/ nb_market_transform (Bronze → Silver → Gold, scheduled via pl_market_transform)
   │        ↓
   │   features_market_1min available for downstream use
   ├── Power BI — Fabric Market Pulse dashboard
   └── Fabric Activator → Email alert
```

## Repository Structure

```text
.
├── README.md
├── LICENSE
├── .gitignore
├── Fabric_Market_Pulse.pbix
├── docs/
│   ├── architecture-diagram.png
│   ├── setup-guide.md
│   └── screenshots/
├── ingestion/
│   ├── binance_to_fabric.py
│   ├── requirements.txt
│   └── config.example.env
├── eventstream/
│   └── eventstream-config-notes.md
├── kql/
│   ├── create_tables.kql
│   ├── latest_price.kql
│   ├── price_trend_1h.kql
│   ├── mover_5min.kql
│   ├── volume_anomaly.kql
│   └── ohlc_view.kql
├── notebooks/
│   └── nb_market_transform.ipynb
├── pipeline/
│   └── pipeline-config-notes.md
├── activator/
│   └── alert-rules-notes.md
└── powerbi/
    ├── market_pulse_theme.json
    └── report-notes.md
```

## ⚡ Stream Ingestion (`ingestion/binance_to_fabric.py`)

Connects to Binance's 24hr mini-ticker WebSocket feed for the configured
symbols (`BTCUSDT`, `ETHUSDT`, `SOLUSDT` by default).

**Key features:**
- **Resilient WebSocket** — automatic reconnection with exponential backoff,
  60s ping/pong heartbeat keep-alives.
- **Kafka protocol compliance** — publishes to the Fabric Eventstream custom
  endpoint using SASL_SSL authentication.
- **Data normalization** — maps the raw Binance payload to a clean schema:

```json
{
  "symbol": "BTCUSDT",
  "price": 63250.12,
  "priceChangePercent": 1.83,
  "volume": 18234.552,
  "high": 63980.00,
  "low": 61200.00,
  "open": 62100.00,
  "eventTime": "2026-09-13T12:05:00.123Z"
}
```

## 📊 Real-Time KQL Queries (`kql/`)

Fabric Eventhouse enables sub-second analytical queries over the streaming
`MarketData` table:

- `latest_price.kql` — latest tick per symbol via `arg_max`.
- `price_trend_1h.kql` — 1-minute-bucketed price trend over the last hour.
- `mover_5min.kql` — 5-minute % price change per symbol:
  ```kql
  MarketData
  | where eventTime > ago(5m)
  | summarize firstPrice = arg_min(eventTime, price), lastPrice = arg_max(eventTime, price) by symbol
  | project symbol, priceChange5Min = round(((lastPrice - firstPrice) / firstPrice) * 100, 3)
  ```
- `volume_anomaly.kql` — flags current volume > 2× the 24h baseline.
- `ohlc_view.kql` — a reusable `OhlcCandles()` function for OHLC candles at
  any interval:
  ```kql
  MarketData
  | summarize open = arg_min(eventTime, price), high = max(price),
              low = min(price), close = arg_max(eventTime, price),
              volume = sum(volume)
    by symbol, bin(eventTime, 5m)
  ```

## 🔔 Fabric Activator & Automated Alerts

Activator watches the KQL stream (and the gold baseline table for volume) to
detect market conditions in real time. Four rules are configured:

| Rule | Condition |
|---|---|
| Significant Price Increase | Price change % > 2% |
| Significant Price Decrease | Price change % < -2% |
| Volume Anomaly | Current volume > 2× baseline volume |
| Large 5-Minute Price Movement | 5-minute price change > 1% |

**Action:** send an email containing the symbol, current price, price
change %, detection time, and reason for the alert. Full details in
[`activator/alert-rules-notes.md`](activator/alert-rules-notes.md).

## 🔄 Data Pipeline & Medallion Architecture

Batch transformation is scheduled via a single Fabric Data pipeline
(`pl_market_transform`) running one Notebook activity:

```text
[pl_market_transform] ──> [Notebook activity: nb_market_transform]
```

`nb_market_transform` (attached to Lakehouse `lh_market`) runs the entire
Medallion flow in one execution:

- **Bronze → Silver** — reads `raw_market_ticks`, casts/cleans types,
  drops nulls, deduplicates, writes `silver_market_ticks`.
- **Silver → Gold (OHLC)** — computes 1-minute Open/High/Low/Close/Volume/
  Trade-count candles into `ohlc_1min`.
- **Gold (features)** — computes `sma_5`, `sma_20`, `volatility_20`,
  `volume_sma_20`, and `volume_ratio` per symbol into `features_market_1min`.
- **Backtest (educational only)** — a simple SMA(5)/SMA(20) crossover
  backtest, displayed in-notebook (not written to a table). This is **not**
  a production trading strategy — it ignores fees, slippage, risk controls,
  and execution constraints.

See [`pipeline/pipeline-config-notes.md`](pipeline/pipeline-config-notes.md)
for the suggested schedule (every 15–60 minutes).

## 📈 Power BI Dashboard

A two-page report (`Fabric_Market_Pulse.pbix`) styled with the project's
custom cyberpunk-fintech theme (`powerbi/market_pulse_theme.json`):

**1. Historical Price Analysis**
- KPI cards (current price, 24h change %, volume)
- Price history table
- Price trend line chart

**2. Volume Analysis**
- KPI cards
- Volume comparison charts across symbols

Details in [`powerbi/report-notes.md`](powerbi/report-notes.md).

## 🛠️ Setup & Local Deployment

Full walkthrough in [`docs/setup-guide.md`](docs/setup-guide.md). Quick version:

```bash
git clone https://github.com/your-username/fabric-market-pulse.git
cd fabric-market-pulse/ingestion
pip install -r requirements.txt
cp config.example.env config.env   # then fill in your real values
python binance_to_fabric.py
```

You'll also need, in your Fabric workspace: an Eventhouse + KQL database
(run `kql/create_tables.kql`), a Lakehouse named `lh_market` (for
`raw_market_ticks` and the notebook's output tables), an Eventstream (see
`eventstream/eventstream-config-notes.md`), and Activator rules configured
per `activator/alert-rules-notes.md`.

## 🛡️ Security

No connection strings, API keys, passwords, Eventstream credentials, or
other secrets are stored in this repository — `.gitignore` excludes
`config.env` and friends. Only `ingestion/config.example.env` (a template)
is committed. Communication between the local ingestion script and Fabric
uses SASL_SSL.

## License

MIT — see [`LICENSE`](LICENSE).
