import os
import json
import asyncio
import aiohttp
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from token_manager import check_and_refresh_on_startup #

load_dotenv()

# Configuration
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = os.getenv("API_URL")
COOLDOWN_SECONDS = 30
user_cooldowns = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message for the bot."""
    await update.message.reply_text(
        "👋 Welcome to Free Fire Like Bot!\n\n"
        "Use /like <server> <uid> to send likes.\n"
        "Example: `/like ind 12345678`"
    )

async def like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /like command."""
    user_id = update.effective_user.id
    
    # Cooldown Logic
    now = datetime.now()
    if user_id in user_cooldowns:
        elapsed = (now - user_cooldowns[user_id]).total_seconds()
        if elapsed < COOLDOWN_SECONDS:
            remaining = int(COOLDOWN_SECONDS - elapsed)
            await update.message.reply_text(f"⏳ Please wait {remaining}s.")
            return

    # Argument Check
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: /like <server> <uid>")
        return

    server = context.args[0].lower()
    uid = context.args[1]

    if not uid.isdigit() or len(uid) < 6: #
        await update.message.reply_text("❌ Invalid UID.")
        return

    user_cooldowns[user_id] = now
    
    # API Call Logic
    async with aiohttp.ClientSession() as session:
        url = f"{API_URL}/like?uid={uid}&server={server}"
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == 1:
                        msg = (
                            f"✅ **LIKE SENT**\n\n"
                            f"👤 Nickname: {data.get('player')}\n"
                            f"🆔 UID: {uid}\n"
                            f"📈 Added: +{data.get('likes_added')}\n"
                            f"📊 Total: {data.get('likes_after')}"
                        )
                    else:
                        msg = "❌ Limit reached for today. Try again in 24h."
                else:
                    msg = "⚠️ API Error or Player Not Found."
                
                await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text("❌ Connection Error.")

def main():
    """Start the bot."""
    application = Application.builder().token(TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("like", like))

    print("🚀 Telegram Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
    