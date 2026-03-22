"""
Shared user/admin access helpers.
"""

from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS, DATABASE_PATH
from utils.storage import UserStore
from utils.ui import build_banned_text

store = UserStore(DATABASE_PATH)


def is_admin(user_id: int) -> bool:
    """Return True when the user ID belongs to a configured admin."""
    return user_id in ADMIN_IDS


def sync_user(update: Update):
    """Upsert the effective Telegram user in storage."""
    return store.upsert_user(update.effective_user)


async def ensure_allowed_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    require_admin: bool = False,
):
    """Register the user and enforce ban/admin checks."""
    user_row = sync_user(update)

    if user_row["is_banned"]:
        await _send_or_alert(update, context, build_banned_text(), alert=True)
        return None

    if require_admin and not is_admin(update.effective_user.id):
        await _send_or_alert(
            update,
            context,
            "<b>Admin Only</b>\n\nThis action is only available to bot admins.",
            alert=True,
        )
        return None

    return user_row


async def _send_or_alert(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    alert: bool = False,
) -> None:
    """Send a message for text updates or alert users from callback queries."""
    if update.callback_query:
        await update.callback_query.answer("Access denied." if alert else "", show_alert=alert)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode=ParseMode.HTML,
        )
        return

    if update.effective_message:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
