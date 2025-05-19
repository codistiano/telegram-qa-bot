import logging
import os
import json
import time
from functools import wraps
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler, InlineQueryHandler
from telegram.error import TelegramError
from dotenv import load_dotenv

from uuid import uuid4

# Loading Environemntal variables
load_dotenv()

ADMIN_ID = int(os.getenv('ADMIN_ID'))

# Admin only function
def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            await update.message.reply_text("You are ot authorized to use this command.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# Importing JSON QA pairs
def load_qa(retries=5, delay=0.1):
    for _ in range(retries):
        try:
            with open('qa.json', 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            time.sleep(delay)
    return {}

# Adding a QA pair
def add_qa_pair(keyword, response):
    qa_pairs = load_qa()
    qa_pairs[keyword] = response
    with open('qa.json', 'w') as f:
        json.dump(qa_pairs, f, indent=4)


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s \n',
    level=logging.WARNING,
    filename='bot.log'
)
logger = logging.getLogger(__name__)

# Hello Command Handler function
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Start command received from user: %s", update.effective_user.id)
    username = update.effective_user.username or "User"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Hello, {username}! I'm your bot. Ask about price, location, or delivery!"
    )

# Capitalize Command Handler function
async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide text to capitalize, e.g., /caps hello world")
        return
    text_caps = ' '.join(context.args).upper()
    await update.message.reply_text(text_caps)

# Adding QA Pairs Command Handler function
@admin_only
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        command_text = ' '.join(context.args)
        if "|" not in command_text:
            await update.message.reply_text("Use format: /add keyword | response")
            return
        
        keyword, response = map(str.strip, command_text.split("|", 1))
        if not keyword or not response:
            await update.message.reply_text("Keyword and response cannot be empty")
            return
        
        add_qa_pair(keyword, response)
        await update.message.reply_text(f"Added Q&A: '{keyword}' → '{response}'")

    except Exception as e:
        logger.error("Error in /add: %s", e)
        await update.message.reply_text("Failed to add. Try again later.")


# Message Handler function
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text.lower()
    qa_pairs = load_qa()

    # Check each keyword
    for keyword in qa_pairs:
        if keyword in message:
            await update.message.reply_text(qa_pairs[keyword])
            return

    # Default reply if no keyword matched
    await update.message.reply_text("Sorry, I don’t understand.")
    return 

# Inline Functionality
async def inline_caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        return
    results = []
    results.append(
        InlineQueryResultArticle(
            id=str(uuid4()),
            title='Caps',
            input_message_content=InputTextMessageContent(query.upper())
        )
    )
    await context.bot.answer_inline_query(update.inline_query.id, results)

# Unknown Command Handler function
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE, valid_commands=None):
    command = update.message.text.split()[0][1:].lower()
    if valid_commands and command in valid_commands:
        return
    logger.info("Unkown command received: %s", update.message.text)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

# Error Handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Update %s caused error %s", update, context.error)
    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="An error occurred. Please try again later."
        )


if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("No TELEGRAM_BOT_TOKEN found in environment variables")
        raise ValueError("Please set TELEGRAM_BOT_TOKEN in .env file")

    command_handlers = [
        CommandHandler('start', start),
        CommandHandler('caps', caps),
        CommandHandler('add', add),
        # Add other command handlers here
    ]

    valid_commands = [list(handler.commands)[0] for handler in command_handlers]

        
    try:
        application = ApplicationBuilder().token(token).build()

        # Define handlers
        handlers = [
            CommandHandler('start', start),
            CommandHandler('caps', caps),
            CommandHandler('add', add),
            InlineQueryHandler(inline_caps),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
        ]

        # Add handlers
        application.add_handlers(handlers, group=0)
        application.add_handler(MessageHandler(filters.COMMAND, lambda update, context: unknown(update, context, valid_commands) ), group=1) # type: ignore
        application.add_error_handler(error_handler)

        logger.info("Bot is starting...")
        print("Bot is starting...")
        application.run_polling()
    except TelegramError as e:
        logger.error("Telegram error: %s", e)
        print(f"Failed to start bot: {e}")
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        print(f"An unexpected error occurred: {e}")
