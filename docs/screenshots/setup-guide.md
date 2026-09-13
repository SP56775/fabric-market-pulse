# Setup Guide — Fabric Market Pulse

End-to-end steps to stand this project up from scratch in a Fabric workspace.

## 1. Prerequisites
- A Microsoft Fabric workspace (Fabric capacity or Trial), Contributor+ access
- Python 3.10+ locally (for the ingestion script)
- A Binance account is **not** required — the public market-data WebSocket
  streams used here don't need API keys

## 2. Create the Fabric items
1. Create an **Eventhouse** (and its default KQL database) in your workspace.
2. Run `kql/create_tables.kql` against that KQL database to create the
   `MarketData` table and its JSON ingestion mapping.
3. Create a **Lakehouse** named `lh_market` — this holds the raw
   `raw_market_ticks` bronze table plus the silver/gold tables produced by
   `notebooks/nb_market_transform.ipynb`.
4. Create an **Eventstream** item with two destinations (Eventhouse +
   Lakehouse). See `eventstream/eventstream-config-notes.md` for the exact
   source/transform/destination configuration, including a schema note you
   should resolve before connecting the Lakehouse destination.
5. Note the workspace ID and eventstream ID from the item's URL — you'll need
   the eventstream's connection details for step 3 below.

## 3. Configure and run ingestion
1. `cd ingestion`
2. `pip install -r requirements.txt`
3. `cp config.example.env config.env`
4. Fill in `config.env` with your Eventstream custom-endpoint connection
   string (from the Eventstream source's "Connection details" pane) and the
   symbols you want to track.
5. `python binance_to_fabric.py`
6. Confirm live traffic in the Eventstream's **Live view**, then confirm rows
   are landing in `MarketData` with `kql/latest_price.kql`.

## 4. (Optional) Set up the scheduled notebook pipeline
1. Import `notebooks/nb_market_transform.ipynb`, attach it to the `lh_market`
   Lakehouse.
2. Create a Data pipeline named `pl_market_transform` with a single
   **Notebook activity** running `nb_market_transform`.
3. Add a Schedule trigger — every 15, 30, or 60 minutes.
4. See `pipeline/pipeline-config-notes.md` for what each stage produces
   (`silver_market_ticks`, `ohlc_1min`, `features_market_1min`) and how
   `volume_ratio` can feed the Volume Anomaly alert rule.

## 5. Build the Power BI report
1. Connect Power BI to the `MarketData` (and gold) tables in your Eventhouse.
2. Apply `powerbi/market_pulse_theme.json` as the report theme.
3. See `powerbi/report-notes.md` for the page/visual layout this project uses.
4. Or start from the included `Fabric_Market_Pulse.pbix` and repoint its
   data source to your own Eventhouse.

## 6. Configure Fabric Activator
1. Point Activator at the `MarketData` Eventhouse table (or its derived
   stream) as the event source.
2. Create the four alert rules described in `README.md` /
   `activator/alert-rules-notes.md`.
3. Set the action to **Send email**, using the subject/body template in
   `activator/alert-rules-notes.md`.
4. Test with a manual trigger, then publish.

## 7. Verify end-to-end
- Ingestion script running → Eventstream Live view shows traffic → rows in
  `MarketData` → Power BI report refreshing → Activator firing a test email.
