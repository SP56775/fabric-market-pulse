# Eventstream Configuration Notes

## Workspace / Item IDs
- Workspace ID: `4cd29df7-4907-46eb-83cd-70eaa738fc07`
- Eventstream ID: `b99dc297-c135-4786-9068-092a3fe7531e`

(No credentials here — connection strings live only in local `config.env`, never committed.)

## Source
- **Type:** Custom endpoint (custom app)
- **Why:** Binance is not a native Fabric connector, so market data is pushed in
  by an external script (`ingestion/binance_to_fabric.py`) over the Kafka
  protocol exposed by the custom endpoint.
- **Auth:** SASL_SSL with the Event Hubs–compatible connection string.

## Event schema (as published by the ingestion script)
| Field | Type | Description |
|---|---|---|
| `symbol` | string | e.g. `BTCUSDT` |
| `price` | real | last traded price |
| `priceChangePercent` | real | 24h % change, from Binance ticker |
| `volume` | real | 24h traded volume |
| `high` / `low` / `open` | real | 24h high/low/open |
| `eventTime` | datetime (ISO 8601) | event timestamp (UTC) |

## Transformations
- **Manage fields:** cast `price`, `volume`, `priceChangePercent` etc. to the
  correct numeric types; rename fields if needed to match the KQL table.
- **Filter (optional):** restrict to `BTCUSDT`, `ETHUSDT`, `SOLUSDT` if the
  source ever broadcasts additional symbols.
- Aggregation for volume baselines is done downstream in KQL
  (`kql/volume_anomaly.kql`) rather than inside Eventstream, to keep the
  stream itself simple and stateless.

## Destination
- **Type:** Eventhouse
- **Ingestion mode:** Event processing before ingestion (since Manage fields /
  Filter are applied upstream)
- **Target table:** `MarketData` (see `kql/create_tables.kql`)
- **Input format:** JSON, mapped with `MarketDataMapping`

## Publish checklist
1. Source connected and showing live traffic in **Live view**.
2. Transformations validated against sample data.
3. Eventhouse destination connected and table mapping confirmed.
4. Eventstream **Published**.
5. Confirm rows landing in `MarketData` via `kql/latest_price.kql`.
