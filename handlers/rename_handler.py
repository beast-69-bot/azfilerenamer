"""
Rename Handler - Rename Flow & ZIP Creation
"""

import os
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from config import TEMP_DIR
from utils.cleaner import TempCleaner
from utils.zipper import ZipCreator

# Conversation states
RENAME_LOOP = 1

zip_creator = ZipCreator(TEMP_DIR)
cleaner = TempCleaner(TEMP_DIR)


async def start_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the rename conversation flow."""
    query = update.callback_query
    await query.answer()

    file_list = context.user_data.get("file_list", [])
    if not file_list:
        await query.edit_message_text("No files to rename.")
        return ConversationHandler.END

    context.user_data["rename_index"] = 0
    context.user_data["renamed_files"] = {}
    context.user_data["original_files"] = file_list.copy()

    return await ask_rename(update, context)


async def ask_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask the user for the new name of the current file."""
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
        f"<b>Rename Files</b> ({rename_idx + 1}/{len(file_list)})\n\n"
        f"Current file: <code>{escape(file_name)}</code>\n\n"
        "Type the new name for this file, or click Skip to keep the same name.\n\n"
        f"Remaining: {remaining} files"
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
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Rename cancelled.\n\nUse /start to begin again or send a new file."
    )

    context.user_data.pop("rename_index", None)
    context.user_data.pop("renamed_files", None)
    context.user_data.pop("original_files", None)

    return ConversationHandler.END


async def create_renamed_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a ZIP with renamed files and send it to the user."""
    extract_path = context.user_data.get("extract_path", "")
    archive_name = context.user_data.get("archive_name", "archive.zip")
    renamed_files = context.user_data.get("renamed_files", {})
    user_id = update.effective_user.id

    try:
        status_message = await _update_status_message(
            update,
            context,
            "Creating ZIP with renamed files. Please wait...",
        )

        zip_path = zip_creator.create_zip(
            extract_path,
            renamed_files,
            archive_name,
            user_id,
        )

        zip_size = zip_creator.get_zip_size(zip_path)
        renamed_count = sum(1 for old_path, new_path in renamed_files.items() if old_path != new_path)

        await status_message.edit_text(
            "ZIP created.\n"
            f"Size: {zip_size}\n"
            f"Renamed: {renamed_count} files\n"
            "Sending..."
        )

        with open(zip_path, "rb") as file_handle:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file_handle,
                filename=os.path.basename(zip_path),
                caption=f"Here is your renamed archive.\nSize: {zip_size}",
            )

        cleaner.cleanup_user_temp(user_id)
        context.user_data.clear()

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="All done. Send another file to continue.",
        )
    except Exception as exc:
        print(f"Error creating ZIP: {exc}")
        if update.callback_query:
            await update.callback_query.edit_message_text(
                f"Error creating ZIP: {exc}\n\nPlease try again."
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Error creating ZIP: {exc}\n\nPlease try again.",
            )

    return ConversationHandler.END


async def _update_status_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
):
    """Edit the current bot message when possible, otherwise send a new one."""
    if update.callback_query:
        await update.callback_query.edit_message_text(text)
        return update.callback_query.message

    return await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
    )
