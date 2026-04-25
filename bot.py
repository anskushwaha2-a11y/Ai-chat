import os
import logging
from dotenv import load_dotenv
import openai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_TOKEN = os.getenv('8648028972:AAE9ej8GdJghkZCAArJB_NDBNCFjO7BsSUg')
OPENAI_API_KEY = os.getenv('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')

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store conversation history for each user (optional)
user_conversations = {}

class TelegramAIBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Register handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("clear", self.clear_command))
        self.application.add_handler(CommandHandler("about", self.about_command))
        self.application.add_handler(CommandHandler("menu", self.menu_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: CallbackContext):
        """Send a welcome message when /start is issued."""
        welcome_text = (
            "🤖 *Welcome to AI Assistant Bot!*\n\n"
            "I'm an AI-powered bot that can help you with various tasks.\n\n"
            "*What I can do:*\n"
            "• Answer questions\n"
            "• Help with coding\n"
            "• Provide explanations\n"
            "• Creative writing\n"
            "• And much more!\n\n"
            "Just send me any message and I'll respond!\n\n"
            "Use /menu to see available commands."
        )
        
        keyboard = [
            [InlineKeyboardButton("📝 Start Chat", callback_data="start_chat")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
            [InlineKeyboardButton("📊 About", callback_data="about")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: CallbackContext):
        """Send help information."""
        help_text = (
            "*Available Commands:*\n\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/clear - Clear conversation history\n"
            "/about - About this bot\n"
            "/menu - Show menu options\n\n"
            "*How to use:*\n"
            "Simply send me any text message and I'll respond using AI!\n\n"
            "*Tips:*\n"
            "• Be specific with your questions\n"
            "• Use /clear to reset our conversation\n"
            "• Ask for code examples, explanations, or creative content"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def about_command(self, update: Update, context: CallbackContext):
        """Send about information."""
        about_text = (
            "*About AI Assistant Bot*\n\n"
            "Version: 1.0.0\n"
            "Powered by: OpenAI GPT-3.5/4\n"
            "Framework: python-telegram-bot v20+\n\n"
            "This bot uses advanced AI to help with various tasks.\n\n"
            "*Features:*\n"
            "• Context-aware conversations\n"
            "• Multi-language support\n"
            "• Code generation and explanation\n"
            "• Secure and private\n\n"
            "Created with ❤️ using Python"
        )
        await update.message.reply_text(about_text, parse_mode='Markdown')
    
    async def menu_command(self, update: Update, context: CallbackContext):
        """Show menu with options."""
        keyboard = [
            [InlineKeyboardButton("🗑️ Clear History", callback_data="clear")],
            [InlineKeyboardButton("🆘 Help", callback_data="help")],
            [InlineKeyboardButton("ℹ️ About", callback_data="about")],
            [InlineKeyboardButton("🔄 New Topic", callback_data="new_topic")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("*Menu:*", reply_markup=reply_markup, parse_mode='Markdown')
    
    async def clear_command(self, update: Update, context: CallbackContext):
        """Clear conversation history for the user."""
        user_id = update.effective_user.id
        if user_id in user_conversations:
            del user_conversations[user_id]
        await update.message.reply_text("✅ Conversation history cleared! Starting fresh.")
    
    async def button_callback(self, update: Update, context: CallbackContext):
        """Handle button callbacks."""
        query = update.callback_query
        await query.answer()
        
        if query.data == "start_chat":
            await query.edit_message_text("Great! Send me any message and I'll help you! 🤖")
        elif query.data == "help":
            await query.edit_message_text(await self.get_help_text(), parse_mode='Markdown')
        elif query.data == "about":
            await query.edit_message_text(await self.get_about_text(), parse_mode='Markdown')
        elif query.data == "clear":
            user_id = update.effective_user.id
            if user_id in user_conversations:
                del user_conversations[user_id]
            await query.edit_message_text("✅ History cleared!")
        elif query.data == "new_topic":
            user_id = update.effective_user.id
            if user_id in user_conversations:
                # Keep only last 2 messages for context
                if len(user_conversations[user_id]) > 2:
                    user_conversations[user_id] = user_conversations[user_id][-2:]
            await query.edit_message_text("Starting new conversation topic! Send your message.")
    
    async def get_help_text(self):
        return (
            "*Help & Support*\n\n"
            "• Send any message to chat with AI\n"
            "• /clear - Reset conversation\n"
            "• /menu - Show options\n\n"
            "*Example questions:*\n"
            "- 'Explain machine learning'\n"
            "- 'Write Python code for fibonacci'\n"
            "- 'Tell me a joke'\n"
            "- 'Summarize this text: [your text]'"
        )
    
    async def get_about_text(self):
        return "*AI Assistant Bot v1.0*\nPowered by OpenAI GPT"
    
    async def get_ai_response(self, user_id: str, user_message: str) -> str:
        """Get response from OpenAI API."""
        try:
            # Prepare messages with conversation history
            messages = []
            
            # Add system message
            messages.append({
                "role": "system",
                "content": "You are a helpful AI assistant. Be concise, friendly, and accurate. For code, use proper formatting."
            })
            
            # Add conversation history (last 5 exchanges)
            if user_id in user_conversations:
                messages.extend(user_conversations[user_id][-10:])  # Last 10 messages for context
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # or "gpt-4" if you have access
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            # Store in conversation history
            if user_id not in user_conversations:
                user_conversations[user_id] = []
            
            user_conversations[user_id].append({"role": "user", "content": user_message})
            user_conversations[user_id].append({"role": "assistant", "content": ai_response})
            
            # Limit conversation history to last 20 messages
            if len(user_conversations[user_id]) > 20:
                user_conversations[user_id] = user_conversations[user_id][-20:]
            
            return ai_response
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return "Sorry, I encountered an error. Please try again later."
    
    async def handle_message(self, update: Update, context: CallbackContext):
        """Handle incoming text messages."""
        user_message = update.message.text
        user_id = update.effective_user.id
        username = update.effective_user.username or "User"
        
        # Send typing action
        await update.message.chat.send_action(action="typing")
        
        # Get AI response
        response = await self.get_ai_response(user_id, user_message)
        
        # Send response (split if too long)
        if len(response) > 4096:
            for x in range(0, len(response), 4096):
                await update.message.reply_text(response[x:x+4096], parse_mode='Markdown')
        else:
            await update.message.reply_text(response, parse_mode='Markdown')
    
    async def error_handler(self, update: Update, context: CallbackContext):
        """Handle errors."""
        logger.error(f"Update {update} caused error {context.error}")
        
        # Send message to user if possible
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again later."
            )
    
    def run(self):
        """Start the bot."""
        logger.info("Starting bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    # Validate environment variables
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
    
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    # Create and run bot
    bot = TelegramAIBot()
    bot.run()