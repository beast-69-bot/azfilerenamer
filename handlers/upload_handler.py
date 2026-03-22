"""
Upload Handler - Single & Bulk Upload Logic
"""

from __future__ import annotations

import asyncio
import os
import time
from html import escape

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from utils.extractor import ArchiveExtractor
from utils.transfer import (
    build_progress_bar,
    format_eta,
    format_size,
    format_speed,
    get_transfer_profile,
)

from .common import ensure_allowed_user, store

extractor = ArchiveExtractor("")


async def upload_single_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Upload a single file based on callback data."""
    user_row = await ensure_allowed_user(update, context)
    if not user_row:
        return

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
    file_size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
    transfer_profile = get_transfer_profile(bool(user_row["is_premium"]))

    try:
        await query.edit_message_text(
            (
                "<b>Single Upload</b>\n\n"
                f"<b>Mode:</b> {escape(transfer_profile.name)}\n"
                f"Uploading <code>{escape(file_name)}</code>...\n"
                f"<b>Size:</b> <code>{format_size(file_size)}</code>"
            ),
            parse_mode=ParseMode.HTML,
        )

        started_at = time.perf_counter()
        with open(full_path, "rb") as file_handle:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file_handle,
                filename=file_name,
                caption=f"Uploaded <code>{escape(file_name)}</code> successfully.",
                parse_mode=ParseMode.HTML,
            )
        elapsed = max(time.perf_counter() - started_at, 0.001)

        store.increment_usage(update.effective_user.id, files_uploaded=1)

        await query.edit_message_text(
            (
                "<b>Single Upload Complete</b>\n\n"
                f"<code>{escape(file_name)}</code> was sent successfully.\n"
                f"<b>Size:</b> <code>{format_size(file_size)}</code>\n"
                f"<b>Average Speed:</b> <code>{format_speed(file_size / elapsed)}</code>\n"
                f"<b>Time:</b> <code>{elapsed:.1f}s</code>"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        print(f"Upload error: {exc}")
        await query.edit_message_text(
            (
                "<b>Upload Failed</b>\n\n"
                f"File: <code>{escape(file_name)}</code>\n"
                f"Reason: <code>{escape(str(exc))}</code>"
            ),
            parse_mode=ParseMode.HTML,
        )


async def upload_all_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Upload all files one by one."""
    user_row = await ensure_allowed_user(update, context)
    if not user_row:
        return

    query = update.callback_query
    await query.answer()

    file_list = context.user_data.get("file_list", [])
    extract_path = context.user_data.get("extract_path", "")

    if not file_list:
        await query.edit_message_text("No files to upload.")
        return

    transfer_profile = get_transfer_profile(bool(user_row["is_premium"]))
    upload_items = []
    for file_path in file_list:
        full_path = extractor.get_full_path(extract_path, file_path)
        size_bytes = os.path.getsize(full_path) if os.path.exists(full_path) else 0
        upload_items.append((file_path, full_path, size_bytes))

    total_files = len(file_list)
    total_bytes = sum(size for _, _, size in upload_items)
    await query.edit_message_text(
        (
            "<b>Bulk Upload Started</b>\n\n"
            f"<b>Mode:</b> {escape(transfer_profile.name)}\n"
            f"<b>Concurrency:</b> <code>{transfer_profile.upload_concurrency}</code>\n"
            f"Progress: <code>0/{total_files}</code>"
        ),
        parse_mode=ParseMode.HTML,
    )
    status_message = query.message

    semaphore = asyncio.Semaphore(transfer_profile.upload_concurrency)
    state = {
        "uploaded_count": 0,
        "failed_count": 0,
        "uploaded_bytes": 0,
        "active_files": [],
    }
    state_lock = asyncio.Lock()
    started_at = time.perf_counter()

    async def upload_one(item) -> None:
        file_path, full_path, size_bytes = item
        file_name = os.path.basename(file_path)

        async with semaphore:
            async with state_lock:
                state["active_files"].append(file_name)

            try:
                with open(full_path, "rb") as file_handle:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=file_handle,
                        filename=file_name,
                    )
                async with state_lock:
                    state["uploaded_count"] += 1
                    state["uploaded_bytes"] += size_bytes
            except Exception as exc:
                print(f"Upload error for {file_name}: {exc}")
                async with state_lock:
                    state["failed_count"] += 1
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=(
                        "<b>One File Failed</b>\n\n"
                        f"<code>{escape(file_name)}</code> could not be uploaded."
                    ),
                    parse_mode=ParseMode.HTML,
                )
            finally:
                async with state_lock:
                    if file_name in state["active_files"]:
                        state["active_files"].remove(file_name)

            if transfer_profile.upload_delay:
                await asyncio.sleep(transfer_profile.upload_delay)

    async def update_status_loop(tasks) -> None:
        last_text = None
        while True:
            async with state_lock:
                text = _build_bulk_upload_status_text(
                    total_files=total_files,
                    total_bytes=total_bytes,
                    profile_name=transfer_profile.name,
                    state=state,
                    started_at=started_at,
                )
            if text != last_text:
                await status_message.edit_text(text, parse_mode=ParseMode.HTML)
                last_text = text

            if all(task.done() for task in tasks):
                break
            await asyncio.sleep(transfer_profile.progress_interval)

    tasks = [asyncio.create_task(upload_one(item)) for item in upload_items]
    status_task = asyncio.create_task(update_status_loop(tasks))
    await asyncio.gather(*tasks)
    await status_task

    if state["uploaded_count"]:
        store.increment_usage(
            update.effective_user.id,
            files_uploaded=state["uploaded_count"],
        )

    elapsed = max(time.perf_counter() - started_at, 0.001)
    summary = (
        "<b>Bulk Upload Complete</b>\n\n"
        f"<b>Mode:</b> {escape(transfer_profile.name)}\n"
        f"Total Files: <code>{total_files}</code>\n"
        f"Uploaded: <code>{state['uploaded_count']}</code>\n"
        f"Failed: <code>{state['failed_count']}</code>\n"
        f"Uploaded Size: <code>{format_size(state['uploaded_bytes'])}</code>\n"
        f"Average Speed: <code>{format_speed(state['uploaded_bytes'] / elapsed)}</code>"
    )
    await status_message.edit_text(summary, parse_mode=ParseMode.HTML)


def _build_bulk_upload_status_text(
    total_files: int,
    total_bytes: int,
    profile_name: str,
    state: dict,
    started_at: float,
) -> str:
    """Build the live bulk upload status text."""
    completed_files = state["uploaded_count"] + state["failed_count"]
    elapsed = max(time.perf_counter() - started_at, 0.001)
    speed = state["uploaded_bytes"] / elapsed
    remaining_bytes = max(total_bytes - state["uploaded_bytes"], 0)
    eta = remaining_bytes / speed if speed > 0 else None
    active_preview = ", ".join(state["active_files"][:2]) if state["active_files"] else "Waiting"
    progress_bar = build_progress_bar(completed_files, total_files or 1)
    percent = (completed_files / total_files * 100) if total_files else 0

    return (
        "<b>Bulk Upload Running</b>\n\n"
        f"<b>Mode:</b> {escape(profile_name)}\n"
        f"<code>{progress_bar}</code> <b>{percent:.1f}%</b>\n"
        f"<b>Files:</b> <code>{completed_files}/{total_files}</code>\n"
        f"<b>Uploaded:</b> <code>{state['uploaded_count']}</code>\n"
        f"<b>Failed:</b> <code>{state['failed_count']}</code>\n"
        f"<b>Transferred:</b> <code>{format_size(state['uploaded_bytes'])}</code> / <code>{format_size(total_bytes)}</code>\n"
        f"<b>Speed:</b> <code>{format_speed(speed)}</code>\n"
        f"<b>ETA:</b> <code>{format_eta(eta)}</code>\n"
        f"<b>Active:</b> <code>{escape(active_preview)}</code>"
    )
