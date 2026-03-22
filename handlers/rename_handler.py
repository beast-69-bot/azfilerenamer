"""
Rename Handler - Rename Flow & ZIP Creation
"""

from __future__ import annotations

import os
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from config import TEMP_DIR
from utils.cleaner import TempCleaner
from utils.zipper import ZipCreator

from .common import ensure_allowed_user, store

RENAME_LOOP = 1

zip_creator = ZipCreator(TEMP_DIR)
cleaner = TempCleaner(TEMP_DIR)


async def start_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the rename conversation flow."""
    if not await ensure_allowed_user(update, context):
        return ConversationHandler.END

    query = update.callback_query
    await query.answer()

    file_list = context.user_data.get("file_list", [])
    if not file_list:
        await query.edit_message_text("No files are loaded for renaming.")
        return ConversationHandler.END

    context.user_data["rename_index"] = 0
    context.user_data["renamed_files"] = {}
    context.user_data["original_files"] = file_list.copy()

    return await ask_rename(update, context)


async def ask_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask the user for a new name for the current file."""
    file_list = context.user_data.get("original_files", [])
    rename_idx = context.user_data.get("rename_index", 0)

    if rename_idx >= len(file_list):
        return await create_renamed_zip(update, context)

    current_file = file_list[rename_idx]
    file_name = os.path.basename(current_file)
    remaining = len(file_list) - rename_idx

    keyboard = [
        [InlineKeyboardButton("Skip", callback_data="rename_skip")],
        [InlineKeyboardButton("Cancel Rename", callback_data="rename_cancel")],
    ]
    message_text = (
        f"<b>Rename Builder</b> ({rename_idx + 1}/{len(file_list)})\n\n"
        f"<b>Current File:</b> <code>{escape(file_name)}</code>\n"
        "Send the new filename in chat, or tap Skip to keep the original.\n\n"
        f"<b>Remaining:</b> <code>{remaining}</code>"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )

    return RENAME_LOOP


async def handle_rename_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle a rename entered by the user."""
    if not await ensure_allowed_user(update, context):
        return ConversationHandler.END

    new_name = update.message.text.strip()
    if not new_name:
        await update.message.reply_text("Filename cannot be empty. Try again:")
        return RENAME_LOOP

    if "/" in new_name or "\\" in new_name:
        await update.message.reply_text(
            "Invalid name. Do not use '/' or '\\' in the filename. Try again:"
        )
        return RENAME_LOOP

    file_list = context.user_data.get("original_files", [])
    rename_idx = context.user_data.get("rename_index", 0)
    renamed_files = context.user_data.get("renamed_files", {})

    current_file = file_list[rename_idx]
    current_parent = os.path.dirname(current_file)
    renamed_path = os.path.join(current_parent, new_name) if current_parent else new_name

    renamed_files[current_file] = renamed_path
    context.user_data["renamed_files"] = renamed_files
    context.user_data["rename_index"] = rename_idx + 1

    return await ask_rename(update, context)


async def skip_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip renaming the current file."""
    if not await ensure_allowed_user(update, context):
        return ConversationHandler.END

    query = update.callback_query
    await query.answer()

    file_list = context.user_data.get("original_files", [])
    rename_idx = context.user_data.get("rename_index", 0)
    renamed_files = context.user_data.get("renamed_files", {})

    current_file = file_list[rename_idx]
    renamed_files[current_file] = current_file
    context.user_data["renamed_files"] = renamed_files
    context.user_data["rename_index"] = rename_idx + 1

    return await ask_rename(update, context)


async def cancel_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the rename process."""
    if not await ensure_allowed_user(update, context):
        return ConversationHandler.END

    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        (
            "<b>Rename Cancelled</b>\n\n"
            "The archive session is still available. Send a new file or open another action."
        ),
        parse_mode=ParseMode.HTML,
    )

    context.user_data.pop("rename_index", None)
    context.user_data.pop("renamed_files", None)
    context.user_data.pop("original_files", None)

    return ConversationHandler.END


async def create_renamed_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a ZIP with renamed files and send it to the user."""
    if not await ensure_allowed_user(update, context):
        return ConversationHandler.END

    extract_path = context.user_data.get("extract_path", "")
    archive_name = context.user_data.get("archive_name", "archive.zip")
    renamed_files = context.user_data.get("renamed_files", {})
    user_id = update.effective_user.id

    try:
        status_message = await _update_status_message(
            update,
            context,
            "<b>Rename Builder</b>\n\nCreating ZIP with renamed files...",
        )

        zip_path = zip_creator.create_zip(
            extract_path,
            renamed_files,
            archive_name,
            user_id,
        )

        zip_size = zip_creator.get_zip_size(zip_path)
        renamed_count = sum(
            1 for old_path, new_path in renamed_files.items() if old_path != new_path
        )

        await status_message.edit_text(
            (
                "<b>ZIP Ready</b>\n\n"
                f"Size: <code>{zip_size}</code>\n"
                f"Renamed Files: <code>{renamed_count}</code>\n"
                "Sending your rebuilt archive..."
            ),
            parse_mode=ParseMode.HTML,
        )

        with open(zip_path, "rb") as file_handle:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file_handle,
                filename=os.path.basename(zip_path),
                caption=(
                    "<b>Renamed Archive Delivered</b>\n"
                    f"Size: <code>{zip_size}</code>"
                ),
                parse_mode=ParseMode.HTML,
            )

        cleaner.cleanup_user_temp(user_id)
        context.user_data.clear()
        store.increment_usage(user_id, zip_exports=1)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "<b>Rename Flow Complete</b>\n\n"
                "Your new ZIP has been sent. Upload another archive whenever you are ready."
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        print(f"Error creating ZIP: {exc}")
        error_text = (
            "<b>Rename ZIP Failed</b>\n\n"
            f"<code>{escape(str(exc))}</code>\n\nPlease try again."
        )
        if update.callback_query:
            await update.callback_query.edit_message_text(
                error_text,
                parse_mode=ParseMode.HTML,
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=error_text,
                parse_mode=ParseMode.HTML,
            )

    return ConversationHandler.END


async def _update_status_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
):
    """Edit the current bot message when possible, otherwise send a new one."""
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML)
        return update.callback_query.message

    return await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
    )
