"""
File Handler - ZIP/RAR Receive & Extract
"""

from __future__ import annotations

import asyncio
import os
import time
from html import escape
from pathlib import Path

import aiohttp

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from config import FILES_PER_PAGE, FREE_MAX_FILE_SIZE, PREMIUM_MAX_FILE_SIZE, TEMP_DIR
from utils.cleaner import TempCleaner
from utils.extractor import ArchiveExtractor
from utils.transfer import (
    build_progress_bar,
    format_eta,
    format_size,
    format_speed,
    get_transfer_profile,
)
from utils.ui import build_archive_overview_text

from .common import ensure_allowed_user, store

extractor = ArchiveExtractor(TEMP_DIR)
cleaner = TempCleaner(TEMP_DIR)


def _archive_action_keyboard() -> InlineKeyboardMarkup:
    """Build the archive action keyboard."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📋 Show File List", callback_data="show_files_0")],
            [
                InlineKeyboardButton("📤 Upload All", callback_data="upload_all"),
                InlineKeyboardButton("✏️ Rename Files", callback_data="rename_files"),
            ],
            [InlineKeyboardButton("📊 My Status", callback_data="menu_status")],
        ]
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming ZIP/RAR documents."""
    user_row = await ensure_allowed_user(update, context)
    if not user_row:
        return

    document = update.message.document
    user_id = update.effective_user.id
    max_file_size = PREMIUM_MAX_FILE_SIZE if user_row["is_premium"] else FREE_MAX_FILE_SIZE

    file_name = (document.file_name or "").lower()
    if not (file_name.endswith(".zip") or file_name.endswith(".rar")):
        await update.message.reply_text(
            "⚠️ <b>Unsupported Format</b>\n\nPlease send a <b>ZIP</b> or <b>RAR</b> file only.",
            parse_mode=ParseMode.HTML,
        )
        return

    if document.file_size and document.file_size > max_file_size:
        max_size_gb = max_file_size / (1024 * 1024 * 1024)
        plan_name = "Premium" if user_row["is_premium"] else "Free"
        await update.message.reply_text(
            (
                "❌ <b>File Too Large</b>\n\n"
                f"<b>Your Plan:</b> {plan_name}\n"
                f"<b>Archive Limit:</b> <code>{max_size_gb:.0f} GB</code>\n\n"
                "Upgrade to premium for a higher limit."
            ),
            parse_mode=ParseMode.HTML,
        )
        return

    processing_msg = await update.message.reply_text(
        "⏳ <b>Processing Archive</b>\n\n⬇️ Downloading your file...",
        parse_mode=ParseMode.HTML,
    )

    try:
        cleaner.cleanup_user_temp(user_id)
        user_temp_dir = cleaner.create_user_temp_dir(user_id)

        download_name = os.path.basename(document.file_name) if document.file_name else "archive"
        file = await context.bot.get_file(document.file_id, read_timeout=3600, write_timeout=3600)
        downloaded_path = os.path.join(user_temp_dir, download_name)
        transfer_profile = get_transfer_profile(bool(user_row["is_premium"]))
        await _download_file_with_progress(
            telegram_file=file,
            destination=downloaded_path,
            total_bytes=document.file_size or 0,
            progress_message=processing_msg,
            profile_name=transfer_profile.name,
            chunk_size=transfer_profile.download_chunk_size,
            progress_interval=transfer_profile.progress_interval,
        )

        await _safe_edit(
            processing_msg,
            "⏳ <b>Processing Archive</b>\n\n📦 Extracting files...",
        )

        success, extract_path, file_list = await asyncio.to_thread(
            extractor.extract_archive,
            downloaded_path,
            user_id,
            download_name,
        )

        if not success:
            await _safe_edit(
                processing_msg,
                (
                    "❌ <b>Extraction Failed</b>\n\n"
                    "The archive could not be extracted.\n"
                    "Please check the file format and integrity."
                ),
            )
            return

        file_count, total_size = extractor.get_file_info(extract_path, file_list)

        context.user_data["extract_path"] = extract_path
        context.user_data["file_list"] = file_list
        context.user_data["archive_name"] = download_name
        context.user_data["downloaded_path"] = downloaded_path

        store.increment_usage(
            user_id,
            archives_processed=1,
            last_archive_name=download_name,
        )

        await _safe_edit(
            processing_msg,
            build_archive_overview_text(download_name, file_count, total_size),
            reply_markup=_archive_action_keyboard(),
        )
    except Exception as exc:
        print(f"Error handling document: {exc}")
        await _safe_edit(
            processing_msg,
            f"❌ <b>Processing Error</b>\n\n<code>{escape(str(exc))}</code>",
        )


async def _safe_edit(message, text: str, reply_markup=None) -> None:
    """Edit a message, silently swallowing Telegram API errors."""
    try:
        await message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
    except TelegramError:
        pass


async def _download_file_with_progress(
    telegram_file,
    destination: str,
    total_bytes: int,
    progress_message,
    profile_name: str,
    chunk_size: int,
    progress_interval: float,
):
    """Stream a Telegram file to disk with live progress updates."""
    url = telegram_file._get_encoded_url()
    Path(destination).parent.mkdir(parents=True, exist_ok=True)

    timeout = aiohttp.ClientTimeout(total=None, connect=30)
    start_time = time.perf_counter()
    last_update = 0.0
    last_text = None
    downloaded = 0

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            response.raise_for_status()
            with open(destination, "wb") as file_handle:
                async for chunk in response.content.iter_chunked(chunk_size):
                    file_handle.write(chunk)
                    downloaded += len(chunk)

                    now = time.perf_counter()
                    if now - last_update < progress_interval:
                        continue

                    text = _build_download_progress_text(
                        downloaded=downloaded,
                        total_bytes=total_bytes,
                        started_at=start_time,
                        profile_name=profile_name,
                    )
                    if text != last_text:
                        try:
                            await progress_message.edit_text(text, parse_mode=ParseMode.HTML)
                            last_text = text
                        except TelegramError:
                            pass
                    last_update = now

    final_text = _build_download_progress_text(
        downloaded=downloaded,
        total_bytes=total_bytes or downloaded,
        started_at=start_time,
        profile_name=profile_name,
        completed=True,
    )
    try:
        await progress_message.edit_text(final_text, parse_mode=ParseMode.HTML)
    except TelegramError:
        pass


def _build_download_progress_text(
    downloaded: int,
    total_bytes: int,
    started_at: float,
    profile_name: str,
    completed: bool = False,
) -> str:
    """Build the download progress message."""
    elapsed = max(time.perf_counter() - started_at, 0.001)
    speed = downloaded / elapsed
    eta = None
    if total_bytes and speed > 0 and not completed:
        eta = max(total_bytes - downloaded, 0) / speed

    percent = (downloaded / total_bytes * 100) if total_bytes else 0
    progress_bar = build_progress_bar(downloaded, total_bytes or downloaded or 1)
    status_line = "✅ Download complete." if completed else "⬇️ Downloading your file..."
    total_label = format_size(total_bytes or downloaded)

    return (
        "⏳ <b>Processing Archive</b>\n\n"
        f"{status_line}\n"
        f"<b>Mode:</b> {escape(profile_name)}\n"
        f"<code>{progress_bar}</code> <b>{percent:.1f}%</b>\n"
        f"<b>Downloaded:</b> <code>{format_size(downloaded)}</code> / <code>{total_label}</code>\n"
        f"<b>Speed:</b> <code>{format_speed(speed)}</code>\n"
        f"<b>ETA:</b> <code>{format_eta(eta)}</code>"
    )


async def show_file_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a paginated file list with upload buttons."""
    if not await ensure_allowed_user(update, context):
        return

    query = update.callback_query
    await query.answer()

    page = int(query.data.split("_")[-1])
    file_list = context.user_data.get("file_list", [])

    if not file_list:
        await query.edit_message_text("No files found for this session.\n\nPlease send a new archive.")
        return

    total_files = len(file_list)
    start_idx = page * FILES_PER_PAGE
    end_idx = min(start_idx + FILES_PER_PAGE, total_files)
    current_files = file_list[start_idx:end_idx]
    total_pages = (total_files + FILES_PER_PAGE - 1) // FILES_PER_PAGE

    lines = [f"📋 <b>File List</b> ({page + 1}/{total_pages})", ""]
    keyboard = []
    row = []

    for file_idx, file_path in enumerate(current_files, start=start_idx):
        display_idx = file_idx + 1
        file_name = os.path.basename(file_path)
        lines.append(f"{display_idx}. <code>{escape(file_name)}</code>")
        row.append(
            InlineKeyboardButton(
                f"📤 {display_idx}",
                callback_data=f"upload_single_{file_idx}",
            )
        )
        if len(row) == 3:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("⬅️ Prev", callback_data=f"show_files_{page - 1}")
        )
    if end_idx < total_files:
        nav_buttons.append(
            InlineKeyboardButton("Next ➡️", callback_data=f"show_files_{page + 1}")
        )
    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append(
        [
            InlineKeyboardButton("📤 Upload All", callback_data="upload_all"),
            InlineKeyboardButton("✏️ Rename Files", callback_data="rename_files"),
        ]
    )
    keyboard.append(
        [InlineKeyboardButton("🔙 Back to Overview", callback_data="back_overview")]
    )

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )


async def back_to_overview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to the archive overview."""
    if not await ensure_allowed_user(update, context):
        return

    query = update.callback_query
    await query.answer()

    file_list = context.user_data.get("file_list", [])
    archive_name = context.user_data.get("archive_name", "Unknown")
    extract_path = context.user_data.get("extract_path", "")

    if not file_list or not extract_path:
        await query.edit_message_text(
            "⚠️ <b>Session Expired</b>\n\n"
            "No archive data found. Please send a new file.",
            parse_mode=ParseMode.HTML,
        )
        return

    file_count = len(file_list)
    total_size = extractor.get_file_info(extract_path, file_list)[1]

    await query.edit_message_text(
        build_archive_overview_text(archive_name, file_count, total_size),
        reply_markup=_archive_action_keyboard(),
        parse_mode=ParseMode.HTML,
    )
