import logging
import time
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram.error import Unauthorized
from threading import Timer
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Configuration ===
TOKEN = "7578919098:AAHTkBkQEn37u9jo5Jitx2lf1DhmQ-qrIqM"
OWNER_USERNAMES = ["spider_spice"]
MIN_JOIN_AMOUNT = 30
JOIN_TIMEOUT = 60  # seconds

# === Logging ===
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# === Google Sheets Auth ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)
sheet = client.open("TelegramBotData").sheet1

# === Matchmaking Queue ===
match_queue = []

# === Helper Functions ===

def is_admin(username):
    return username in OWNER_USERNAMES

def get_user_row(username):
    users = sheet.col_values(1)[1:]
    try:
        return users.index(username) + 2
    except ValueError:
        return None

def get_balance(username):
    row = get_user_row(username)
    if row:
        return int(sheet.cell(row, 2).value)
    return 0

def dm_user(bot, user_id, text):
    try:
        bot.send_message(chat_id=user_id, text=text)
    except Unauthorized:
        pass

def delete_message(context: CallbackContext, chat_id, message_id):
    try:
        context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass

# === Bot Commands ===

def register_command(update: Update, context: CallbackContext):
    username = update.effective_user.username
    if not username:
        dm_user(context.bot, update.effective_user.id, "❌ Please set a Telegram username.")
        return
    if get_user_row(username):
        dm_user(context.bot, update.effective_user.id, "✅ Already registered.")
    else:
        sheet.append_row([username, "0", "", ""])
        dm_user(context.bot, update.effective_user.id, "✅ Registration complete!")

def join_command(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    username = update.effective_user.username

    if not username:
        dm_user(context.bot, update.effective_user.id, "❌ Please set a Telegram username.")
        delete_message(context, chat_id, message_id)
        return

    if len(context.args) != 1 or not context.args[0].isdigit():
        dm_user(context.bot, update.effective_user.id, "❌ Usage: /join <amount>")
        delete_message(context, chat_id, message_id)
        return

    amount = int(context.args[0])
    if amount < MIN_JOIN_AMOUNT:
        dm_user(context.bot, update.effective_user.id, f"❌ Minimum join amount is ₹{MIN_JOIN_AMOUNT}")
        delete_message(context, chat_id, message_id)
        return

    if not get_user_row(username):
        dm_user(context.bot, update.effective_user.id, "❌ Not registered. Use /register in DM.")
        delete_message(context, chat_id, message_id)
        return

    context.bot_data.setdefault("pending_joins", {})[username] = {
        "amount": amount,
        "timestamp": time.time(),
        "chat_id": chat_id,
        "message_id": message_id
    }

    # Match check
    for other_username, data in list(context.bot_data["pending_joins"].items()):
        if other_username != username and data["amount"] == amount:
            match_msg = f"🤝 Match Found:\n@{username} vs @{other_username}\nAmount: ₹{amount}"
            context.bot.send_message(chat_id=chat_id, text=match_msg)
            delete_message(context, data["chat_id"], data["message_id"])
            delete_message(context, chat_id, message_id)
            del context.bot_data["pending_joins"][other_username]
            del context.bot_data["pending_joins"][username]
            return

    # Timeout logic
    def remove_if_unmatched():
        join = context.bot_data["pending_joins"].get(username)
        if join and time.time() - join["timestamp"] >= JOIN_TIMEOUT:
            delete_message(context, join["chat_id"], join["message_id"])
            del context.bot_data["pending_joins"][username]
            dm_user(context.bot, update.effective_user.id, "⏳ No match found in 1 minute. You were removed from the queue.")

    Timer(JOIN_TIMEOUT, remove_if_unmatched).start()

def leave_command(update: Update, context: CallbackContext):
    username = update.effective_user.username
    if username in context.bot_data.get("pending_joins", {}):
        del context.bot_data["pending_joins"][username]
        dm_user(context.bot, update.effective_user.id, "❎ You have left the queue.")
    delete_message(context, update.effective_chat.id, update.message.message_id)

def balance_command(update: Update, context: CallbackContext):
    username = update.effective_user.username
    balance = get_balance(username)
    text = f"💰 Your balance: ₹{balance}"
    if update.effective_chat.type == "private":
        update.message.reply_text(text)
    else:
        dm_user(context.bot, update.effective_user.id, text)
        delete_message(context, update.effective_chat.id, update.message.message_id)

def group_message_filter(update: Update, context: CallbackContext):
    username = update.effective_user.username
    text = update.message.text
    message_id = update.message.message_id
    chat_id = update.effective_chat.id

    if is_admin(username):
        return

    allowed_commands = ["/join", "/leave", "/balance"]
    if any(text.startswith(cmd) for cmd in allowed_commands):
        return

    delete_message(context, chat_id, message_id)
    dm_user(context.bot, update.effective_user.id, "⚠️ Please use this command in DM.")

# === Main ===
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("register", register_command))
    dp.add_handler(CommandHandler("join", join_command))
    dp.add_handler(CommandHandler("leave", leave_command))
    dp.add_handler(CommandHandler("balance", balance_command))
    dp.add_handler(MessageHandler(Filters.text & Filters.group, group_message_filter))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
