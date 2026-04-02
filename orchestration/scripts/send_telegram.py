"""
Send a Telegram alert with anomaly signals for a given trading date.

Reads /data/anomalies_{date}.json (written by detect_anomalies.py) and posts
a formatted message to a Telegram bot.

Required environment variables:
    TELEGRAM_BOT_TOKEN  - from @BotFather
    TELEGRAM_CHAT_ID    - your personal chat ID or a group/channel ID

Usage:
    python orchestration/scripts/send_telegram.py 2025-03-28
"""

import json
import os
import sys
from html import escape
from pathlib import Path
import urllib.request


def _post(bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
    ).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Telegram API returned {resp.status}")


def _format_message(ds: str, anomalies: list[dict]) -> str:
    safe_ds = escape(ds)
    if not anomalies:
        return f"<b>FinSight Daily Signals - {safe_ds}</b>\n\nNo anomalies detected today."

    lines = [
        f"<b>FinSight Daily Signals - {safe_ds}</b>",
        f"{len(anomalies)} signal(s) detected:\n",
    ]

    for anomaly in anomalies:
        tags = []
        if anomaly.get("is_oversold"):
            tags.append("OVERSOLD")
        if anomaly.get("is_overbought"):
            tags.append("OVERBOUGHT")
        if anomaly.get("is_volume_spike"):
            tags.append("VOL SPIKE")
        if anomaly.get("is_large_move"):
            tags.append("LARGE MOVE")

        tag_str = " | ".join(tags) if tags else "Signal"
        pct = anomaly.get("pct_change") or 0
        rsi = anomaly.get("rsi_14") or 0
        volume_zscore = anomaly.get("volume_zscore") or 0
        close = anomaly.get("close") or 0
        symbol = escape(str(anomaly.get("symbol", "n/a")))
        sector = escape(str(anomaly.get("sector", "")))

        lines.append(
            f"<b>{symbol}</b> ({sector})\n"
            f"  Close: ${close:.2f}  Chg: {pct:+.2f}%  RSI: {rsi:.1f}  VolZ: {volume_zscore:.2f}\n"
            f"  <i>{escape(tag_str)}</i>"
        )

    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: send_telegram.py <YYYY-MM-DD>", file=sys.stderr)
        sys.exit(1)

    ds = sys.argv[1]
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        print("[send_telegram] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set - skipping alert")
        sys.exit(0)

    anomaly_file = Path(f"/data/anomalies_{ds}.json")
    if not anomaly_file.exists():
        print(f"[send_telegram] {anomaly_file} not found - run detect_anomalies.py first")
        sys.exit(1)

    data = json.loads(anomaly_file.read_text())
    anomalies = data.get("anomalies", [])

    message = _format_message(ds, anomalies)
    _post(bot_token, chat_id, message)
    print(f"[send_telegram] Alert sent for {ds} ({len(anomalies)} anomalies)")


if __name__ == "__main__":
    main()
