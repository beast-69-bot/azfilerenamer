"""
Telegram File Manager Bot - Main Entry Point

A Python-based Telegram Bot that handles ZIP and RAR files:
- Extract and view file contents
- Upload files individually or all at once  
- Rename files before downloading
- Get a new ZIP with renamed files

Usage:
    1. Set your BOT_TOKEN in config.py or as environment variable
    2. Run: python bot.py
"""

import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)

# Import configuration
from config import BOT_TOKEN

# Import handlers
from handlers import (
    start_command,
    help_command,
    handle_document,
    show_file_list,
    back_to_overview,
    upload_single_file,
    upload_all_files,
    start_rename,
    handle_rename_input,
    skip_rename,
    cancel_rename,
    RENAME_LOOP
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    await update.message.reply_text(
        "❌ Operation cancelled.\n\n"
        "Send me a ZIP or RAR file to start again!"
    )
    return ConversationHandler.END


def main():
    """Start the bot"""
    # Check for bot token
    token = BOT_TOKEN
    if token == "YOUR_BOT_TOKEN_HERE":
        token = os.environ.get("BOT_TOKEN")
    
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        print("❌ Error: BOT_TOKEN not set!")
        print("Please set your bot token in config.py or as environment variable.")
        print("\nTo get a bot token:")
        print("1. Message @BotFather on Telegram")
        print("2. Create a new bot with /newbot")
        print("3. Copy the token and set it in config.py")
        return
    
    print("🤖 Starting Telegram File Manager Bot...")
    print("=" * 50)
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add rename conversation handler
    rename_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_rename, pattern="^rename_files$")
        ],
        states={
            RENAME_LOOP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rename_input),
                CallbackQueryHandler(skip_rename, pattern="^rename_skip$"),
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_rename, pattern="^rename_cancel$"),
            CommandHandler("cancel", cancel_command),
        ],
    )
    application.add_handler(rename_conv_handler)
    
    # Add callback query handlers
    application.add_handler(CallbackQueryHandler(show_file_list, pattern="^show_files_"))
    application.add_handler(CallbackQueryHandler(upload_single_file, pattern="^upload_single_"))
    application.add_handler(CallbackQueryHandler(upload_all_files, pattern="^upload_all$"))
    application.add_handler(CallbackQueryHandler(back_to_overview, pattern="^back_overview$"))
    
    # Add document handler for ZIP/RAR files
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Error handler
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Log errors"""
        logger.error(f"Update {update} caused error {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again or send /start to restart."
            )
    
    application.add_error_handler(error_handler)
    
    print("✅ Bot is running!")
    print("📱 Send /start to your bot on Telegram")
    print("=" * 50)
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
