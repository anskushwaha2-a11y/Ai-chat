import os
import asyncio
import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_BASE_URL = os.getenv("AI_BASE_URL")
AI_MODEL = os.getenv("AI_MODEL", "gpt-3.5-turbo")

# Store conversation history per user
user_histories = {}

# System prompt that defines the bot's behavior
SYSTEM_PROMPT = {
    "role": "system",
    "content": "You are a helpful, friendly AI assistant. Keep responses concise but informative."
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_message = (
        "🤖 *Hello! I'm your AI Assistant Bot*\n\n"
        "I can help you with:\n"
        "• Answering questions\n"
        "• Having conversations\n"
        "• Processing images (send a photo with a question)\n\n"
        "Commands:\n"
        "/start - Show this menu\n"
        "/clear - Clear conversation history\n"
        "/help - Get help\n\n"
        "Just send me a message to get started!"
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "*How to use this bot:*\n\n"
        "• Send any text message - I'll respond with AI\n"
        "• Send a photo with a caption - I can see and answer about images\n"
        "• Send a voice message - I'll transcribe and respond\n"
        "• /clear - Reset our conversation (clears memory)\n\n"
        "Made with ❤️ using Python and Railway"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command - reset conversation history"""
    user_id = update.effective_user.id
    if user_id in user_histories:
        del user_histories[user_id]
    await update.message.reply_text("🗑️ Conversation history cleared! I've forgotten our previous chat.")


async def get_ai_response(user_id: int, user_message: str, image_url: str = None):
    """Call AI API and get response with streaming"""
    
    # Initialize user history if not exists
    if user_id not in user_histories:
        user_histories[user_id] = [SYSTEM_PROMPT]
    
    # Add user message to history
    user_histories[user_id].append({"role": "user", "content": user_message})
    
    # Keep only last 20 messages to manage token usage
    if len(user_histories[user_id]) > 21:  # 1 system + 20 messages
        user_histories[user_id] = [SYSTEM_PROMPT] + user_histories[user_id][-20:]
    
    # Prepare the request
    messages = user_histories[user_id].copy()
    
    # If image is provided, format as vision message
    if image_url:
        messages[-1] = {
            "role": "user",
            "content": [
                {"type": "text", "text": user_message},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{AI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": AI_MODEL,
                "messages": messages,
                "stream": True
            }
        )
        
        # Process streaming response
        full_response = ""
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    import json
                    chunk = json.loads(data)
                    if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get("content"):
                        content = chunk["choices"][0]["delta"]["content"]
                        full_response += content
                        yield content
                except:
                    pass
        
        # Save assistant response to history
        if full_response:
            user_histories[user_id].append({"role": "assistant", "content": full_response})


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Send typing indicator
    await update.message.chat.send_action(action="typing")
    
    try:
        # Send initial message that we'll edit as stream comes in
        streaming_message = await update.message.reply_text("🤔 Thinking...")
        
        full_response = ""
        async for chunk in get_ai_response(user_id, user_message):
            full_response += chunk
            
            # Update message every few chunks (Telegram has rate limits)
            if len(full_response) - len(streaming_message.text) > 50:
                try:
                    await streaming_message.edit_text(
                        full_response + " ✍️",
                        parse_mode=None  # Disable Markdown to avoid errors
                    )
                except:
                    pass
        
        # Final update without the typing indicator
        if full_response:
            # Split long responses if needed (Telegram max 4096 chars)
            if len(full_response) > 4000:
                for i in range(0, len(full_response), 4000):
                    await update.message.reply_text(full_response[i:i+4000])
                await streaming_message.delete()
            else:
                await streaming_message.edit_text(full_response)
        else:
            await streaming_message.edit_text("❌ Sorry, I couldn't generate a response. Please try again.")
            
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again later.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos with captions"""
    user_id = update.effective_user.id
    
    # Get the largest photo
    photo_file = await update.message.photo[-1].get_file()
    photo_url = photo_file.file_path
    
    # Get caption or use default
    caption = update.message.caption or "What's in this image?"
    
    await update.message.chat.send_action(action="typing")
    
    try:
        streaming_message = await update.message.reply_text("🖼️ Analyzing image...")
        
        full_response = ""
        async for chunk in get_ai_response(user_id, caption, photo_url):
            full_response += chunk
            if len(full_response) - len(streaming_message.text) > 50:
                try:
                    await streaming_message.edit_text(full_response + " ✍️")
                except:
                    pass
        
        if full_response:
            await streaming_message.edit_text(full_response)
        else:
            await streaming_message.edit_text("❌ Couldn't analyze the image. Please try again.")
            
    except Exception as e:
        print(f"Error in photo handler: {e}")
        await update.message.reply_text("❌ Error processing image. Make sure your AI provider supports vision.")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages"""
    await update.message.reply_text("🎙️ Voice messages are supported! Send a voice note and I'll respond.")
    # For full voice transcription, you'd need a speech-to-text API like Whisper
    # This is a simplified placeholder


def main():
    """Start the bot"""
    if not TELEGRAM_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN not set in .env file")
        return
    
    if not AI_API_KEY:
        print("❌ Error: AI_API_KEY not set in .env file")
        return
    
    # Create application
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_history))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    # Start the bot
    print("🤖 Bot is running... Press Ctrl+C to stop")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()