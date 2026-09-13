# Data Activator Rules

1. alert_price_spike_5min — pct_change > 2%, grouped by symbol
2. alert_price_dump_5min — pct_change < -2%, grouped by symbol
3. alert_data_stale — no events for > 60 seconds
4. alert_volume_anomaly — volume > 3x baseline
