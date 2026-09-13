import json
import os
import time
from datetime import datetime, timezone

import websocket
from azure.eventhub import EventHubProducerClient, EventData
from dotenv import load_dotenv


load_dotenv()

FABRIC_CONN_STR = os.getenv("FABRIC_EVENTSTREAM_CONNECTION_STRING")
PRODUCTS = os.getenv("PRODUCTS", "BTC-USD,ETH-USD,SOL-USD").split(",")

COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"


if not FABRIC_CONN_STR:
    raise ValueError("Missing FABRIC_EVENTSTREAM_CONNECTION_STRING in .env file")


producer = EventHubProducerClient.from_connection_string(
    conn_str=FABRIC_CONN_STR
)


def safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def normalize_ticker_message(message: dict):
    """
    Convert Coinbase ticker message into a clean Fabric-friendly schema.
    """

    if message.get("type") != "ticker":
        return None

    event_time = message.get("time")
    symbol = message.get("product_id")
    price = safe_float(message.get("price"))

    if not event_time or not symbol or price is None:
        return None

    return {
        "event_time": event_time,
        "symbol": symbol,
        "price": price,
        "last_size": safe_float(message.get("last_size")),
        "best_bid": safe_float(message.get("best_bid")),
        "best_ask": safe_float(message.get("best_ask")),
        "side": message.get("side"),
        "exchange": "Coinbase",
        "ingest_utc": datetime.now(timezone.utc).isoformat()
    }


def send_to_fabric(payload: dict):
    event_body = json.dumps(payload)
    event = EventData(event_body)
    producer.send_event(event)


def on_open(ws):
    print("Connected to Coinbase WebSocket")

    subscribe_message = {
        "type": "subscribe",
        "product_ids": PRODUCTS,
        "channels": ["ticker"]
    }

    ws.send(json.dumps(subscribe_message))
    print(f"Subscribed to: {PRODUCTS}")


def on_message(ws, raw_message):
    try:
        message = json.loads(raw_message)

        payload = normalize_ticker_message(message)

        if payload:
            send_to_fabric(payload)
            print(payload)

    except Exception as e:
        print(f"Error processing message: {e}")


def on_error(ws, error):
    print(f"WebSocket error: {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"WebSocket closed: {close_status_code} - {close_msg}")


def run_forever():
    while True:
        try:
            ws = websocket.WebSocketApp(
                COINBASE_WS_URL,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )

            ws.run_forever(
                ping_interval=30,
                ping_timeout=10
            )

        except KeyboardInterrupt:
            print("Stopping...")
            producer.close()
            break

        except Exception as e:
            print(f"Unexpected error: {e}")

        print("Reconnecting in 5 seconds...")
        time.sleep(5)


if __name__ == "__main__":
    run_forever()
