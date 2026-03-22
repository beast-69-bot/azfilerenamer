"""
Dashboard, user features, and admin commands.
"""

from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from utils.ui import (
    build_admin_panel_text,
    build_help_text,
    build_home_text,
    build_main_menu,
    build_plan_text,
    build_status_text,
    build_tasks_text,
)

from .common import ensure_allowed_user, is_admin, store


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open the main dashboard."""
    user_row = await ensure_allowed_user(update, context)
    if not user_row:
        return

    admin_state = is_admin(update.effective_user.id)
    await update.message.reply_text(
        build_home_text(user_row, admin_state),
        parse_mode=ParseMode.HTML,
        reply_markup=build_main_menu(admin_state),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the help screen."""
    user_row = await ensure_allowed_user(update, context)
    if not user_row:
        return

    admin_state = is_admin(update.effective_user.id)
    await update.message.reply_text(
        build_help_text(admin_state),
        parse_mode=ParseMode.HTML,
        reply_markup=build_main_menu(admin_state),
    )


async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the current plan details."""
    user_row = await ensure_allowed_user(update, context)
    if not user_row:
        return

    await update.message.reply_text(
        build_plan_text(user_row),
        parse_mode=ParseMode.HTML,
        reply_markup=build_main_menu(is_admin(update.effective_user.id)),
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the user's account status."""
    user_row = await ensure_allowed_user(update, context)
    if not user_row:
        return

    admin_state = is_admin(update.effective_user.id)
    await update.message.reply_text(
        build_status_text(user_row, admin_state),
        parse_mode=ParseMode.HTML,
        reply_markup=build_main_menu(admin_state),
    )


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the task/features panel."""
    user_row = await ensure_allowed_user(update, context)
    if not user_row:
        return

    await update.message.reply_text(
        build_tasks_text(user_row),
        parse_mode=ParseMode.HTML,
        reply_markup=build_main_menu(is_admin(update.effective_user.id)),
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main dashboard navigation callbacks."""
    user_row = await ensure_allowed_user(update, context)
    if not user_row:
        return

    query = update.callback_query
    await query.answer()
    admin_state = is_admin(update.effective_user.id)
    action = query.data.removeprefix("menu_")

    if action == "home":
        text = build_home_text(user_row, admin_state)
    elif action == "plan":
        text = build_plan_text(user_row)
    elif action == "status":
        text = build_status_text(user_row, admin_state)
    elif action == "tasks":
        text = build_tasks_text(user_row)
    elif action == "help":
        text = build_help_text(admin_state)
    elif action == "admin":
        if not admin_state:
            await query.answer("Admin only.", show_alert=True)
            return
        text = build_admin_panel_text(store.get_stats())
    else:
        text = build_home_text(user_row, admin_state)

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=build_main_menu(admin_state),
    )


async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the admin panel."""
    user_row = await ensure_allowed_user(update, context, require_admin=True)
    if not user_row:
        return

    await update.message.reply_text(
        build_admin_panel_text(store.get_stats()),
        parse_mode=ParseMode.HTML,
        reply_markup=build_main_menu(True),
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin statistics."""
    user_row = await ensure_allowed_user(update, context, require_admin=True)
    if not user_row:
        return

    await update.message.reply_text(
        build_admin_panel_text(store.get_stats()),
        parse_mode=ParseMode.HTML,
        reply_markup=build_main_menu(True),
    )


async def add_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Grant premium access to a user."""
    if not await ensure_allowed_user(update, context, require_admin=True):
        return
    target_id = _extract_target_id(context.args)
    if target_id is None:
        await update.message.reply_text("Usage: /addpremium USER_ID")
        return

    user_row = store.set_premium(target_id, True)
    await update.message.reply_text(
        (
            "<b>Premium Updated</b>\n\n"
            f"User <code>{target_id}</code> now has <b>Premium</b> status.\n"
            f"Premium Since: {_safe_db_value(user_row['premium_since'])}"
        ),
        parse_mode=ParseMode.HTML,
    )


async def remove_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove premium access from a user."""
    if not await ensure_allowed_user(update, context, require_admin=True):
        return
    target_id = _extract_target_id(context.args)
    if target_id is None:
        await update.message.reply_text("Usage: /removepremium USER_ID")
        return

    store.set_premium(target_id, False)
    await update.message.reply_text(
        (
            "<b>Premium Updated</b>\n\n"
            f"User <code>{target_id}</code> is now back on the <b>Free</b> plan."
        ),
        parse_mode=ParseMode.HTML,
    )


async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user from the bot."""
    if not await ensure_allowed_user(update, context, require_admin=True):
        return
    target_id = _extract_target_id(context.args)
    if target_id is None:
        await update.message.reply_text("Usage: /ban USER_ID")
        return
    if is_admin(target_id):
        await update.message.reply_text("Configured admins cannot be banned from inside the bot.")
        return

    store.set_banned(target_id, True)
    await update.message.reply_text(
        f"<b>User Banned</b>\n\nUser <code>{target_id}</code> is now blocked.",
        parse_mode=ParseMode.HTML,
    )


async def unban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a user."""
    if not await ensure_allowed_user(update, context, require_admin=True):
        return
    target_id = _extract_target_id(context.args)
    if target_id is None:
        await update.message.reply_text("Usage: /unban USER_ID")
        return

    store.set_banned(target_id, False)
    await update.message.reply_text(
        f"<b>User Unbanned</b>\n\nUser <code>{target_id}</code> can use the bot again.",
        parse_mode=ParseMode.HTML,
    )


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a text broadcast to all active users."""
    if not await ensure_allowed_user(update, context, require_admin=True):
        return

    message_text = " ".join(context.args).strip()
    if not message_text and update.message.reply_to_message:
        message_text = (
            update.message.reply_to_message.text
            or update.message.reply_to_message.caption
            or ""
        ).strip()

    if not message_text:
        await update.message.reply_text(
            "Usage: /broadcast MESSAGE\nYou can also reply to a message with /broadcast."
        )
        return

    sent_count = 0
    failed_count = 0
    for user_id in store.list_broadcast_targets():
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode=ParseMode.HTML,
            )
            sent_count += 1
        except TelegramError:
            failed_count += 1

    await update.message.reply_text(
        (
            "<b>Broadcast Finished</b>\n\n"
            f"Delivered: <code>{sent_count}</code>\n"
            f"Failed: <code>{failed_count}</code>"
        ),
        parse_mode=ParseMode.HTML,
    )


def _extract_target_id(args: list[str]) -> int | None:
    """Parse a Telegram user ID from command arguments."""
    if not args:
        return None
    value = args[0].strip()
    if not value.lstrip("-").isdigit():
        return None
    return int(value)


def _safe_db_value(value) -> str:
    """Format nullable values for admin confirmations."""
    return str(value) if value else "Not set"
