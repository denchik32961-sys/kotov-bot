import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")


def send_telegram(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        # Чтобы не падало молча, но и не ломало webhook
        print("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Telegram send error:", e)


def fmt_num(x):
    """Аккуратно форматируем числа (и строки-числа)."""
    if x is None:
        return "—"
    try:
        v = float(x)
        # если очень маленькие — больше знаков
        if abs(v) < 1:
            return f"{v:.6f}".rstrip("0").rstrip(".")
        return f"{v:.4f}".rstrip("0").rstrip(".")
    except Exception:
        return str(x)


def build_signal_text(data: dict) -> str:
    symbol = data.get("symbol", "UNKNOWN")
    tf = data.get("tf", "15")
    side = str(data.get("side", "SHORT")).upper()

    z1 = fmt_num(data.get("z1"))
    z2 = fmt_num(data.get("z2"))
    z3 = fmt_num(data.get("z3"))
    sl = fmt_num(data.get("sl"))
    tp1 = fmt_num(data.get("tp1"))
    tp2 = fmt_num(data.get("tp2"))
    risk = data.get("risk_pct", 2.5)
    comment = data.get("comment", "Kotov: pump→dump")

    # Чёткий, “не тильтовый” формат
    text = (
        f"📌 {symbol} | {tf}m\n"
        f"🟥 Сетап: {side} (pump→dump)\n\n"
        f"Зоны продавца:\n"
        f"Z1: {z1}\n"
        f"Z2: {z2}\n"
        f"Z3: {z3}\n\n"
        f"SL: {sl}\n"
        f"TP1: {tp1}\n"
        f"TP2: {tp2}\n"
        f"Risk: {risk}%\n\n"
        f"🧠 Правило: НЕ входить с рынка. Только от зон.\n"
        f"📝 {comment}"
    )
    return text


@app.route("/")
def home():
    return "Kotov bot is alive"


# Основной endpoint для TradingView
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}

    # Проверка секрета (обязательна)
    if WEBHOOK_SECRET:
        if str(data.get("secret", "")) != str(WEBHOOK_SECRET):
            return jsonify({"error": "unauthorized"}), 403

    # Если пришел "message" (текстовый режим) — пересылаем как есть
    if "message" in data and isinstance(data.get("message"), str):
        send_telegram(f"📡 Signal received:\n{data.get('message')}")
        return jsonify({"status": "ok", "mode": "message"})

    # Иначе собираем структурированный сигнал
    text = build_signal_text(data)
    send_telegram(text)
    return jsonify({"status": "ok", "mode": "structured"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
