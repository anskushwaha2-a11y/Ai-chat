# Install dependencies
pip install python-telegram-bot openai python-dotenv

# Create .env file with your tokens
echo "TELEGRAM_BOT_TOKEN=8648028972:AAE9ej8GdJghkZCAArJB_NDBNCFjO7BsSUg" > .env
echo "OPENAI_API_KEY=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" >> .env

# Run the bot
python bot.py