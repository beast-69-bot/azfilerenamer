"""
Telegram File Manager Bot - Main Entry Point
"""

import logging
import os
import signal
import sys

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import (
    BOT_API_BASE_FILE_URL,
    BOT_API_BASE_URL,
    BOT_API_LOCAL_MODE,
    BOT_TOKEN,
    BOT_TITLE,
)
from handlers import (
    RENAME_LOOP,
    add_premium_command,
    admin_panel_command,
    back_to_overview,
    ban_user_command,
    broadcast_command,
    cancel_rename,
    handle_document,
    handle_rename_input,
    help_command,
    menu_callback,
    plan_command,
    remove_premium_command,
    show_file_list,
    skip_rename,
    start_command,
    start_rename,
    stats_command,
    status_command,
    tasks_command,
    unban_user_command,
    upload_all_files,
    upload_single_file,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Suppress noisy HTTP logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the active conversation flow."""
    await update.message.reply_text(
        "❌ Operation cancelled.\n\nSend a ZIP or RAR file to start again."
    )
    return ConversationHandler.END


def main():
    """Start the bot."""
    token = BOT_TOKEN
    if token == "YOUR_BOT_TOKEN_HERE":
        token = os.environ.get("BOT_TOKEN")

    if not token or token == "YOUR_BOT_TOKEN_HERE":
        print("❌ Error: BOT_TOKEN not set.")
        print("Set BOT_TOKEN in .env, config.py, or the environment before running.")
        return

    print(f"🤖 Starting {BOT_TITLE}...")

    application = (
        Application.builder()
        .token(token)
        .base_url(BOT_API_BASE_URL)
        .base_file_url(BOT_API_BASE_FILE_URL)
        .local_mode(BOT_API_LOCAL_MODE)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(30)
        .pool_timeout(30)
        .concurrent_updates(True)
        .build()
    )

    # ── User commands ──
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("plan", plan_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("tasks", tasks_command))

    # ── Admin commands ──
    application.add_handler(CommandHandler("admin", admin_panel_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("addpremium", add_premium_command))
    application.add_handler(CommandHandler("removepremium", remove_premium_command))
    application.add_handler(CommandHandler("ban", ban_user_command))
    application.add_handler(CommandHandler("unban", unban_user_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))

    # ── Rename conversation ──
    rename_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_rename, pattern="^rename_files$")],
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
        per_message=False,
    )
    application.add_handler(rename_conv_handler)

    # ── Callback query handlers ──
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_"))
    application.add_handler(CallbackQueryHandler(show_file_list, pattern="^show_files_"))
    application.add_handler(CallbackQueryHandler(upload_single_file, pattern="^upload_single_"))
    application.add_handler(CallbackQueryHandler(upload_all_files, pattern="^upload_all$"))
    application.add_handler(CallbackQueryHandler(back_to_overview, pattern="^back_overview$"))

    # ── Document handler ──
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # ── Error handler ──
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Log errors and notify the user."""
        logger.error("Update %s caused error %s", update, context.error)
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "⚠️ An error occurred. Please try again or send /start to reset."
                )
            except Exception:
                pass

    application.add_error_handler(error_handler)

    print(f"✅ {BOT_TITLE} is running. Send /start to your bot on Telegram.")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
