# simple_ai_bot.py
import os
import openai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Get tokens from environment
TELEGRAM_TOKEN = os.getenv('8648028972:AAE9ej8GdJghkZCAArJB_NDBNCFjO7BsSUg')
OPENAI_API_KEY = os.getenv('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')

openai.api_key = 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

async def start(update: Update, context):
    await update.message.reply_text("Hello! I'm an AI bot. Send me any message!")

async def handle_message(update: Update, context):
    user_message = update.message.text
    
    # Show typing indicator
    await update.message.chat.send_action(action="typing")
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_message}],
            max_tokens=500
        )
        
        ai_response = response.choices[0].message.content
        await update.message.reply_text(ai_response)
        
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# Create and run bot
app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot is running...")
app.run_polling()