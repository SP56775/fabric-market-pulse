# Fabric Activator – Market Pulse Alerts

## Overview

Microsoft Fabric Activator is used to monitor real-time market data and trigger alerts when predefined conditions are met.

The Market Pulse project uses Activator to monitor price movements and market anomalies, and to send email notifications when alert conditions are satisfied.

## Data Source

The Activator monitors real-time market data produced by the Fabric Real-Time Intelligence pipeline.

```text
Binance
   ↓
Eventstream
   ↓
Eventhouse / KQL
   ↓
Market data
   ↓
Fabric Activator
```

## Alert Rules

### 1. Significant Price Increase

**Purpose:** Detect a rapid increase in cryptocurrency price.

**Condition:**
- Price change percentage > 0.01%

**Action:**
- Send email notification.

**Example alert:**
> BTCUSDT price increased by more than 0.01%.

### 2. Significant Price Decrease

**Purpose:** Detect a rapid decrease in cryptocurrency price.

**Condition:**
- Price change percentage < -0.01%

**Action:**
- Send email notification.

**Example alert:**
> BTCUSDT price decreased by more than 2%.


**Condition:**
- 5-minute price change > 0.01%

**Action:**
- Send email notification.

**Example alert:**
> SOLUSDT moved more than 0.01% in the last 5 minutes.

## Alert Action

The primary action configured for the project is:

**Action:** Send an email notification.

The notification should contain:
- Cryptocurrency symbol
- Current price
- Price change percentage
- Detection time

## Security

No connection strings, API keys, passwords, Eventstream credentials, or other secrets should be stored in this repository.

Secrets are maintained separately in the local environment/configuration.

## Project Role

Activator provides the final event-driven alerting layer:

```text
Real-Time Market Data
        ↓
Eventstream
        ↓
Eventhouse / KQL
        ↓
Market Conditions
        ↓
Fabric Activator
        ↓
Alert Rule
        ↓
Email Notification
```
