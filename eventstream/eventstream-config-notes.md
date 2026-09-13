# Eventstream Configuration

- Source: Custom endpoint (BinanceTradesSource), SAS Key Authentication
- Destinations:
  1. Eventhouse → MarketKQL.LiveTrades (Direct ingestion, Payload only)
  2. Lakehouse → MarketLakehouse.bronze_trades (JSON, Payload only)
- Schema association: OFF (needed for dual destination support)
