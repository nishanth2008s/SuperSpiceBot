Telegram Match Bot Setup Guide

STEP 1: Replace YOUR_BOT_TOKEN_HERE in bot.py with your BotFather token.
STEP 2: Replace creds.json with your real Google Service Account credentials.
STEP 3: Create a Google Sheet named "TelegramBotData" with columns:
    A1: Username
    B1: Amount
STEP 4: Share the sheet with your service account email from creds.json.
STEP 5: Install requirements:
    pip install -r requirements.txt
STEP 6: Run the bot:
    python bot.py

Commands:
/register - Register your username in the sheet
/join <amount> - Join match queue
/balance - View your balance (sent via private message)

To host 24x7, upload this project to Railway or Replit.
