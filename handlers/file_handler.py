"""
File Handler - ZIP/RAR Receive & Extract
"""

import os
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import (
    FILES_PER_PAGE,
    HELP_MESSAGE,
    MAX_FILE_SIZE,
    TEMP_DIR,
    WELCOME_MESSAGE,
)
from utils.cleaner import TempCleaner
from utils.extractor import ArchiveExtractor

# Initialize utilities
extractor = ArchiveExtractor(TEMP_DIR)
cleaner = TempCleaner(TEMP_DIR)


def _build_overview_text(archive_name: str, file_count: int, total_size: str) -> str:
    """Build the archive overview message."""
    return (
        "<b>Archive Overview</b>\n\n"
        f"<b>Name:</b> <code>{escape(archive_name)}</code>\n"
        f"<b>Files:</b> {file_count} files found\n"
        f"<b>Total Size:</b> {total_size}\n\n"
        "What would you like to do?"
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        WELCOME_MESSAGE,
        parse_mode=ParseMode.MARKDOWN,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        HELP_MESSAGE,
        parse_mode=ParseMode.MARKDOWN,
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming documents (ZIP/RAR files)."""
    document = update.message.document
    user_id = update.effective_user.id

    file_name = (document.file_name or "").lower()
    if not (file_name.endswith(".zip") or file_name.endswith(".rar")):
        await update.message.reply_text("Please send only ZIP or RAR files.")
        return

    if document.file_size and document.file_size > MAX_FILE_SIZE:
        max_size_mb = MAX_FILE_SIZE / (1024 * 1024)
        await update.message.reply_text(
            f"File is too large. Maximum supported size is {max_size_mb:.0f} MB."
        )
        return

    processing_msg = await update.message.reply_text(
        "Downloading your file. Please wait..."
    )

    try:
        cleaner.cleanup_user_temp(user_id)
        user_temp_dir = cleaner.create_user_temp_dir(user_id)

        download_name = document.file_name or "archive"
        file = await context.bot.get_file(document.file_id)
        downloaded_path = os.path.join(user_temp_dir, download_name)
        await file.download_to_drive(downloaded_path)

        await processing_msg.edit_text("Extracting files. Please wait...")

        success, extract_path, file_list = extractor.extract_archive(
            downloaded_path,
            user_id,
            download_name,
        )

        if not success:
            await processing_msg.edit_text(
                "Failed to extract archive. Check that the file is valid and safe."
            )
            return

        file_count, total_size = extractor.get_file_info(extract_path, file_list)

        context.user_data["extract_path"] = extract_path
        context.user_data["file_list"] = file_list
        context.user_data["archive_name"] = download_name
        context.user_data["downloaded_path"] = downloaded_path

        keyboard = [
            [InlineKeyboardButton("Show File List", callback_data="show_files_0")],
            [
                InlineKeyboardButton("Upload All", callback_data="upload_all"),
                InlineKeyboardButton("Rename Files", callback_data="rename_files"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await processing_msg.edit_text(
            _build_overview_text(download_name, file_count, total_size),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        print(f"Error handling document: {exc}")
        await processing_msg.edit_text(f"Error processing file: {exc}")


async def show_file_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a paginated file list with upload buttons."""
    query = update.callback_query
    await query.answer()

    page = int(query.data.split("_")[-1])
    file_list = context.user_data.get("file_list", [])

    if not file_list:
        await query.edit_message_text("No files found.")
        return

    total_files = len(file_list)
    start_idx = page * FILES_PER_PAGE
    end_idx = min(start_idx + FILES_PER_PAGE, total_files)
    current_files = file_list[start_idx:end_idx]
    total_pages = (total_files + FILES_PER_PAGE - 1) // FILES_PER_PAGE

    file_list_lines = [f"<b>File List</b> (Page {page + 1}/{total_pages})", ""]
    keyboard = []
    row = []

    for file_idx, file_path in enumerate(current_files, start=start_idx):
        display_idx = file_idx + 1
        file_name = os.path.basename(file_path)
        file_list_lines.append(f"{display_idx}. <code>{escape(file_name)}</code>")
        row.append(
            InlineKeyboardButton(
                f"Upload {display_idx}",
                callback_data=f"upload_single_{file_idx}",
            )
        )

        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("Prev", callback_data=f"show_files_{page - 1}")
        )
    if end_idx < total_files:
        nav_buttons.append(
            InlineKeyboardButton("Next", callback_data=f"show_files_{page + 1}")
        )
    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append(
        [
            InlineKeyboardButton("Upload All", callback_data="upload_all"),
            InlineKeyboardButton("Rename Files", callback_data="rename_files"),
        ]
    )
    keyboard.append(
        [InlineKeyboardButton("Back to Overview", callback_data="back_overview")]
    )

    await query.edit_message_text(
        "\n".join(file_list_lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )


async def back_to_overview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to the overview message."""
    query = update.callback_query
    await query.answer()

    file_list = context.user_data.get("file_list", [])
    archive_name = context.user_data.get("archive_name", "Unknown")
    extract_path = context.user_data.get("extract_path", "")

    file_count = len(file_list)
    total_size = (
        extractor.get_file_info(extract_path, file_list)[1] if extract_path else "0 B"
    )

    keyboard = [
        [InlineKeyboardButton("Show File List", callback_data="show_files_0")],
        [
            InlineKeyboardButton("Upload All", callback_data="upload_all"),
            InlineKeyboardButton("Rename Files", callback_data="rename_files"),
        ],
    ]

    await query.edit_message_text(
        _build_overview_text(archive_name, file_count, total_size),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )
