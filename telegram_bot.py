import os
import json
import asyncio
import aiohttp
import threading
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from token_manager import check_and_refresh_on_startup, check_token_validity

# .env file load karein
load_dotenv()

# --- Flask Server (Render/Hosting ke liye) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Bot is Online and Active!"

def run_flask():
    # Render default port 10000 use karta hai
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- Configuration ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = os.getenv("API_URL")
COOLDOWN_SECONDS = 30
user_cooldowns = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message jab user /start likhe."""
    await update.message.reply_text(
        "👋 **Welcome to Free Fire Like Bot!**\n\n"
        "Use `/like <server> <uid>` to send likes.\n"
        "Example: `/like ind 3955506016`",
        parse_mode="Markdown"
    )

async def like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /like command."""
    user_id = update.effective_user.id
    now = datetime.now()
    
    # Cooldown Logic
    if user_id in user_cooldowns:
        elapsed = (now - user_cooldowns[user_id]).total_seconds()
        if elapsed < COOLDOWN_SECONDS:
            remaining = int(COOLDOWN_SECONDS - elapsed)
            await update.message.reply_text(f"⏳ Please wait {remaining}s before next request.")
            return

    # Check Arguments
    if len(context.args) < 2:
        await update.message.reply_text("❌ **Usage:** `/like <server> <uid>`\nExample: `/like ind 12345678`", parse_mode="Markdown")
        return

    server = context.args[0].lower()
    uid = context.args[1]

    # UID Validation
    if not uid.isdigit() or len(uid) < 6:
        await update.message.reply_text("❌ **Invalid UID.** It must be numbers and at least 6 digits.")
        return

    user_cooldowns[user_id] = now
    
    # API Call
    async with aiohttp.ClientSession() as session:
        # Render server thoda slow ho sakta hai isliye timeout 20s rakha hai
        url = f"{API_URL}/like?uid={uid}&server={server}"
        try:
            async with session.get(url, timeout=20) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == 1:
                        msg = (
                            f"✅ **LIKE SENT SUCCESSFULLY**\n\n"
                            f"👤 **Nickname:** {data.get('player', 'Unknown')}\n"
                            f"🆔 **UID:** {uid}\n"
                            f"📈 **Added:** +{data.get('likes_added', 0)}\n"
                            f"📊 **After:** {data.get('likes_after', 'N/A')}\n\n"
                            f"🔗 *Join Group for Updates!*"
                        )
                    else:
                        msg = "❌ **Limit Reached!** This UID has already received max likes today."
                elif response.status == 503:
                    msg = "⚠️ **Service Waking Up!** Render server is starting, please try again in 1 minute."
                else:
                    msg = f"⚠️ **API Error ({response.status})**: Player not found or server issue."
                
                await update.message.reply_text(msg, parse_mode="Markdown")
        except asyncio.TimeoutError:
            await update.message.reply_text("⏳ **Timeout:** API server took too long to respond. Try again.")
        except Exception as e:
            print(f"Error: {e}")
            await update.message.reply_text("❌ **Connection Error:** Could not connect to API.")

async def post_init(application: Application):
    """Bot start hote hi tokens refresh aur validity check shuru karega."""
    session = aiohttp.ClientSession()
    print("🔄 Initializing tokens and background tasks...")
    await check_and_refresh_on_startup(session)
    asyncio.create_task(check_token_validity(session))

def main():
    """Start the Telegram Bot."""
    if not TOKEN:
        print("❌ Error: TELEGRAM_TOKEN not found in .env")
        return

    # Start Flask in Background Thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Build Telegram App
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("like", like))

    print("🚀 Telegram Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
    
