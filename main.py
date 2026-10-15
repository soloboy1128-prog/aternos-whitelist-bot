import os
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

pending = {}

def send_message(chat_id, text, keyboard=None):
    data = {"chat_id": chat_id, "text": text}
    if keyboard:
        data["reply_markup"] = keyboard
    requests.post(f"{BASE_URL}/sendMessage", json=data, timeout=15)

@app.route("/")
def home():
    return "Whitelist Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(silent=True) or {}

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text = msg.get("text", "").strip()

        if text == "/start":
            send_message(
                chat_id,
                "Welcome!\n\n"
                "Submit your Minecraft Gamertag:\n"
                "/whitelist YourGamertag"
            )

        elif text == "/myid":
            send_message(chat_id, f"Your Telegram ID: {user_id}")

        elif text.startswith("/whitelist "):
            gamertag = text.split(" ", 1)[1].strip()

            if not gamertag or len(gamertag) > 32:
                send_message(chat_id, "Invalid Gamertag.")
                return "OK"

            request_id = str(update["update_id"])
            pending[request_id] = {
                "chat_id": chat_id,
                "user_id": user_id,
                "gamertag": gamertag
            }

            send_message(chat_id, "Request sent to Admin!")

            if ADMIN_ID:
                keyboard = {
                    "inline_keyboard": [[
                        {"text": "✅ Approve",
                         "callback_data": f"approve:{request_id}"},
                        {"text": "❌ Reject",
                         "callback_data": f"reject:{request_id}"}
                    ]]
                }

                send_message(
                    ADMIN_ID,
                    f"Whitelist Request\n"
                    f"Player: {gamertag}\n"
                    f"Telegram ID: {user_id}",
                    keyboard
                )

    elif "callback_query" in update:
        query = update["callback_query"]
        user_id = query["from"]["id"]
        data = query.get("data", "")

        if user_id != ADMIN_ID or ADMIN_ID == 0:
            requests.post(
                f"{BASE_URL}/answerCallbackQuery",
                json={
                    "callback_query_id": query["id"],
                    "text": "Admin only!",
                    "show_alert": True
                },
                timeout=15
            )
            return "OK"

        action, request_id = data.split(":", 1)
        item = pending.pop(request_id, None)

        if item:
            tag = item["gamertag"]

            if action == "approve":
                send_message(
                    item["chat_id"],
                    f"✅ Approved: {tag}\n\n"
                    "Admin must add your Gamertag manually in "
                    "Aternos > Players > Whitelist."
                )
            else:
                send_message(
                    item["chat_id"],
                    f"❌ Request rejected: {tag}"
                )

            send_message(
                ADMIN_ID,
                f"{action.title()}: {tag}\n"
                "Aternos whitelist changes must be done manually."
            )

        requests.post(
            f"{BASE_URL}/answerCallbackQuery",
            json={"callback_query_id": query["id"]},
            timeout=15
        )

    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
