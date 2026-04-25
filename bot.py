"""
Telegram AI Bot with Multi-Provider Support
Supports: OpenAI GPT, Google Gemini, OpenRouter (LLaMA, Claude, etc.)
Features: Conversation memory, streaming responses, model switching
"""

import os
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message.py)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration from .env
TELEGRAM_TOKEN = os.getenv("8648028972:AAE9ej8GdJghkZCAArJB_NDBNCFjO7BsSUg")
OPENAI_API_KEY = os.getenv("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")
GEMINI_API_KEY = os.getenv("AIzaSyBuu0GefnytK4XyOGB2BLAmqZKuo8AnT4E")
OPENROUTER_API_KEY = os.getenv("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")
ALLOWED_USERS = [int(x.strip()) for x in os.getenv("1006321372", "").split(",") if x.strip()]

# AI Models Configuration
AI_PROVIDERS = {
    "openai": {
        "name": "🤖 OpenAI GPT-4",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        "default": "gpt-4o-mini",
        "api_key": OPENAI_API_KEY,
    },
    "gemini": {
        "name": "🌟 Google Gemini",
        "models": ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"],
        "default": "gemini-2.0-flash-exp",
        "api_key": GEMINI_API_KEY,
    },
    "openrouter": {
        "name": "🌐 OpenRouter (Multi-Model)",
        "models": ["google/gemini-2.0-flash-exp:free", "meta-llama/llama-3.2-3b-instruct:free", "microsoft/phi-3-mini-128k:free"],
        "default": "google/gemini-2.0-flash-exp:free",
        "api_key": OPENROUTER_API_KEY,
    },
}

# User conversation history storage
user_conversations: Dict[int, list] = {}
user_providers: Dict[int, str] = {}  # Track which AI provider each user uses
user_models: Dict[int, str] = {}  # Track which model each user uses

MAX_HISTORY = 20  # Maximum conversation history per user
SYSTEM_PROMPT = "You are a helpful, friendly AI assistant. Provide clear and accurate responses."


def check_user_access(user_id: int) -> bool:
    """Check if user is authorized to use the bot."""
    if not ALLOWED_USERS:
        return True
    return user_id in ALLOWED_USERS


async def get_ai_response_openai(prompt: str, history: list, model: str) -> str:
    """Get response from OpenAI API."""
    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history[-MAX_HISTORY:])
        messages.append({"role": "user", "content": prompt})
        
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return f"❌ AI Error: {str(e)}"


async def get_ai_response_gemini(prompt: str, history: list, model: str) -> str:
    """Get response from Google Gemini API."""
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Gemini uses different model names
        model_name = model.replace("gemini-", "")
        if not model_name.startswith("gemini"):
            model_name = f"models/{model}"
        
        gemini_model = genai.GenerativeModel(model_name)
        
        # Build conversation context
        chat = gemini_model.start_chat(history=[])
        
        # Add conversation history
        for msg in history[-MAX_HISTORY:]:
            if msg["role"] == "user":
                chat.send_message(msg["content"])
        
        response = chat.send_message(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return f"❌ AI Error: {str(e)}"


async def get_ai_response_openrouter(prompt: str, history: list, model: str) -> str:
    """Get response from OpenRouter API (access to multiple LLMs)."""
    try:
        import httpx
        
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history[-MAX_HISTORY:])
        messages.append({"role": "user", "content": prompt})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1000,
                },
                timeout=30.0,
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                return f"❌ API Error: {response.text}"
    except Exception as e:
        logger.error(f"OpenRouter API error: {e}")
        return f"❌ AI Error: {str(e)}"


async def get_ai_response(
    prompt: str, user_id: int, provider: str = None, model: str = None
) -> str:
    """Route to appropriate AI provider."""
    if provider is None:
        provider = user_providers.get(user_id, "openai")
    
    if model is None:
        model = user_models.get(user_id, AI_PROVIDERS[provider]["default"])
    
    history = user_conversations.get(user_id, [])
    
    # Route to the correct provider
    if provider == "openai":
        return await get_ai_response_openai(prompt, history, model)
    elif provider == "gemini":
        return await get_ai_response_gemini(prompt, history, model)
    elif provider == "openrouter":
        return await get_ai_response_openrouter(prompt, history, model)
    else:
        return "❌ Invalid AI provider selected."


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user_id = update.effective_user.id
    
    if not check_user_access(user_id):
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    # Initialize user data
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    if user_id not in user_providers:
        user_providers[user_id] = "openai"
    if user_id not in user_models:
        user_models[user_id] = AI_PROVIDERS["openai"]["default"]
    
    welcome_text = (
        "🤖 *Welcome to AI Telegram Bot!*\n\n"
        "I'm an AI-powered assistant that can help you with various tasks.\n\n"
        "*Available Commands:*\n"
        "• `/ai` - Ask me anything (or just send any message)\n"
        "• `/clear` - Clear conversation history\n"
        "• `/model` - Change AI model/provider\n"
        "• `/help` - Show this help message\n\n"
        f"*Current AI:* {AI_PROVIDERS[user_providers[user_id]]['name']}\n"
        f"*Current Model:* `{user_models[user_id]}`\n\n"
        "Just send me a message and I'll respond!"
    )
    
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    user_id = update.effective_user.id
    
    help_text = (
        "*🤖 AI Bot Help*\n\n"
        "*Commands:*\n"
        "• `/start` - Initialize the bot\n"
        "• `/help` - Show this help\n"
        "• `/clear` - Clear conversation memory\n"
        "• `/model` - Switch AI model/provider\n"
        "• `/status` - Show current bot status\n\n"
        "*Features:*\n"
        "• 💬 Natural conversation with memory\n"
        "• 🔄 Multiple AI providers supported\n"
        "• 🎯 Context-aware responses\n"
        "• ⚡ Fast response times\n\n"
        "*Tips:*\n"
        "• Be specific in your questions\n"
        "• Use `/clear` if responses become repetitive\n"
        "• Switch models using `/model` for different tasks"
    )
    
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history for the user."""
    user_id = update.effective_user.id
    
    if user_id in user_conversations:
        user_conversations[user_id] = []
        await update.message.reply_text("🧹 Conversation history cleared!")
    else:
        await update.message.reply_text("No conversation history to clear.")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current bot status."""
    user_id = update.effective_user.id
    
    history_count = len(user_conversations.get(user_id, []))
    provider = user_providers.get(user_id, "openai")
    model = user_models.get(user_id, AI_PROVIDERS[provider]["default"])
    
    status_text = (
        f"*📊 Bot Status*\n\n"
        f"*User ID:* `{user_id}`\n"
        f"*Messages in memory:* {history_count}/{MAX_HISTORY}\n"
        f"*AI Provider:* {AI_PROVIDERS[provider]['name']}\n"
        f"*Current Model:* `{model}`\n"
        f"*Status:* 🟢 Online\n"
        f"*Uptime:* Active\n\n"
        f"Use `/model` to change AI provider or model"
    )
    
    await update.message.reply_text(status_text, parse_mode="Markdown")


async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show model selection menu."""
    keyboard = []
    
    # Create keyboard for provider selection
    for provider_id, provider_info in AI_PROVIDERS.items():
        if provider_info["api_key"]:  # Only show if API key is configured
            keyboard.append([
                InlineKeyboardButton(
                    f"{provider_info['name']}", 
                    callback_data=f"provider_{provider_id}"
                )
            ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🤖 *Select AI Provider:*\n\nChoose which AI service to use:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses for model selection."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data.startswith("provider_"):
        provider = data.replace("provider_", "")
        if provider in AI_PROVIDERS:
            user_providers[user_id] = provider
            user_models[user_id] = AI_PROVIDERS[provider]["default"]
            
            # Show model selection for this provider
            keyboard = []
            for model in AI_PROVIDERS[provider]["models"]:
                keyboard.append([
                    InlineKeyboardButton(model, callback_data=f"model_{provider}_{model}")
                ])
            
            keyboard.append([InlineKeyboardButton("◀️ Back to Providers", callback_data="back_to_providers")])
            
            await query.edit_message_text(
                f"✅ *Provider changed to:* {AI_PROVIDERS[provider]['name']}\n\n"
                f"*Current model:* `{user_models[user_id]}`\n\n"
                f"Select a specific model:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    elif data.startswith("model_"):
        parts = data.split("_", 2)
        provider = parts[1]
        model = parts[2]
        
        user_providers[user_id] = provider
        user_models[user_id] = model
        
        await query.edit_message_text(
            f"✅ *Model updated!*\n\n"
            f"*Provider:* {AI_PROVIDERS[provider]['name']}\n"
            f"*Model:* `{model}`\n\n"
            f"Continue chatting to test the new model!",
            parse_mode="Markdown"
        )
    
    elif data == "back_to_providers":
        keyboard = []
        for provider_id, provider_info in AI_PROVIDERS.items():
            if provider_info["api_key"]:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{provider_info['name']}", 
                        callback_data=f"provider_{provider_id}"
                    )
                ])
        
        await query.edit_message_text(
            "🤖 *Select AI Provider:*\n\nChoose which AI service to use:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages and generate AI responses."""
    user_id = update.effective_user.id
    
    if not check_user_access(user_id):
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    user_message = update.message.text
    if not user_message:
        return
    
    # Send typing indicator
    await update.message.chat.send_action(action="typing")
    
    # Add user message to history
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    # Get AI response
    try:
        response = await get_ai_response(user_message, user_id)
        
        # Add to conversation history
        user_conversations[user_id].append({"role": "user", "content": user_message})
        user_conversations[user_id].append({"role": "assistant", "content": response})
        
        # Keep only last MAX_HISTORY messages
        if len(user_conversations[user_id]) > MAX_HISTORY * 2:
            user_conversations[user_id] = user_conversations[user_id][-MAX_HISTORY * 2:]
        
        # Send response (split if too long)
        if len(response) > 4096:
            for x in range(0, len(response), 4096):
                await update.message.reply_text(response[x:x+4096])
        else:
            await update.message.reply_text(response)
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await update.message.reply_text(
            "❌ Sorry, I encountered an error. Please try again later."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot."""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred. The developers have been notified."
        )


def main():
    """Main function to run the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("No Telegram token provided!")
        return
    
    # Check which AI providers are available
    available_providers = []
    if OPENAI_API_KEY:
        available_providers.append("OpenAI")
    if GEMINI_API_KEY:
        available_providers.append("Gemini")
    if OPENROUTER_API_KEY:
        available_providers.append("OpenRouter")
    
    if not available_providers:
        logger.error("No AI API keys configured! Please set at least one API key.")
        return
    
    logger.info(f"Starting bot with AI providers: {', '.join(available_providers)}")
    
    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("model", model_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    # Start bot
    logger.info("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()