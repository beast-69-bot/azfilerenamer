"""
Upload Handler - Single & Bulk Upload Logic
"""

import asyncio
import os
from html import escape

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import UPLOAD_DELAY
from utils.extractor import ArchiveExtractor

extractor = ArchiveExtractor("")


async def upload_single_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Upload a single file based on callback data."""
    query = update.callback_query
    await query.answer()

    file_idx = int(query.data.split("_")[-1])
    file_list = context.user_data.get("file_list", [])
    extract_path = context.user_data.get("extract_path", "")

    if not file_list or file_idx >= len(file_list):
        await query.edit_message_text("File not found.")
        return

    file_path = file_list[file_idx]
    full_path = extractor.get_full_path(extract_path, file_path)
    file_name = os.path.basename(file_path)

    try:
        await query.edit_message_text(
            f"Uploading <code>{escape(file_name)}</code>...",
            parse_mode=ParseMode.HTML,
        )

        with open(full_path, "rb") as file_handle:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file_handle,
                filename=file_name,
                caption=f"Uploaded <code>{escape(file_name)}</code> successfully.",
                parse_mode=ParseMode.HTML,
            )

        await query.edit_message_text(
            f"Uploaded <code>{escape(file_name)}</code> successfully.",
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        print(f"Upload error: {exc}")
        await query.edit_message_text(
            f"Error uploading <code>{escape(file_name)}</code>: {escape(str(exc))}",
            parse_mode=ParseMode.HTML,
        )


async def upload_all_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Upload all files one by one."""
    query = update.callback_query
    await query.answer()

    file_list = context.user_data.get("file_list", [])
    extract_path = context.user_data.get("extract_path", "")

    if not file_list:
        await query.edit_message_text("No files to upload.")
        return

    total_files = len(file_list)
    await query.edit_message_text(
        f"Starting upload of {total_files} files...\nProgress: 0/{total_files}"
    )
    status_message = query.message

    uploaded_count = 0
    failed_count = 0

    for idx, file_path in enumerate(file_list):
        full_path = extractor.get_full_path(extract_path, file_path)
        file_name = os.path.basename(file_path)

        try:
            if idx % 5 == 0 or idx == total_files - 1:
                await status_message.edit_text(
                    "Uploading files...\n"
                    f"Progress: {idx}/{total_files}\n"
                    f"Uploaded: {uploaded_count}\n"
                    f"Failed: {failed_count}\n\n"
                    f"Current: <code>{escape(file_name)}</code>",
                    parse_mode=ParseMode.HTML,
                )

            with open(full_path, "rb") as file_handle:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file_handle,
                    filename=file_name,
                )

            uploaded_count += 1
            await asyncio.sleep(UPLOAD_DELAY)
        except Exception as exc:
            print(f"Upload error for {file_name}: {exc}")
            failed_count += 1
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Failed to upload <code>{escape(file_name)}</code>.",
                parse_mode=ParseMode.HTML,
            )

    summary = (
        "<b>Upload Complete</b>\n\n"
        f"<b>Total Files:</b> {total_files}\n"
        f"<b>Uploaded:</b> {uploaded_count}\n"
        f"<b>Failed:</b> {failed_count}"
    )
    await status_message.edit_text(summary, parse_mode=ParseMode.HTML)
