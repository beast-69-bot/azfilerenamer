"""
UI helpers for Telegram messages and keyboards.
"""

from __future__ import annotations

from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import BOT_TITLE, FREE_PLAN_NAME, PREMIUM_PLAN_NAME


def _safe(value: str | None) -> str:
    """Escape user-provided values for HTML output."""
    return escape(value or "Unknown")


def plan_name(user_row) -> str:
    """Return the formatted plan name for a user."""
    return PREMIUM_PLAN_NAME if user_row["is_premium"] else FREE_PLAN_NAME


def plan_badge(user_row) -> str:
    """Return a plan badge with emoji."""
    if user_row["is_premium"]:
        return f"⭐ {PREMIUM_PLAN_NAME}"
    return f"🆓 {FREE_PLAN_NAME}"


def build_main_menu(is_admin: bool) -> InlineKeyboardMarkup:
    """Build the primary dashboard keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📊 My Status", callback_data="menu_status"),
            InlineKeyboardButton("💎 Plans", callback_data="menu_plan"),
        ],
        [
            InlineKeyboardButton("📋 Tasks", callback_data="menu_tasks"),
            InlineKeyboardButton("❓ Help", callback_data="menu_help"),
        ],
        [InlineKeyboardButton("🏠 Home", callback_data="menu_home")],
    ]
    if is_admin:
        keyboard.insert(
            2,
            [InlineKeyboardButton("🛡️ Admin Panel", callback_data="menu_admin")],
        )
    return InlineKeyboardMarkup(keyboard)


def build_home_text(user_row, is_admin: bool) -> str:
    """Build the main welcome dashboard."""
    role = "🛡️ Admin" if is_admin else "👤 User"
    return (
        f"🤖 <b>{BOT_TITLE}</b>\n"
        "<i>Archive tools with user management and premium-ready controls.</i>\n\n"
        f"<b>User:</b> {_safe(user_row['first_name'])}\n"
        f"<b>ID:</b> <code>{user_row['user_id']}</code>\n"
        f"<b>Role:</b> {role}\n"
        f"<b>Plan:</b> {plan_badge(user_row)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📦 <b>How To Use</b>\n\n"
        "1️⃣ Send a ZIP or RAR file.\n"
        "2️⃣ Review the extracted file list.\n"
        "3️⃣ Upload files, rename them, or rebuild a ZIP.\n\n"
        "Use the dashboard buttons below to manage your account."
    )


def build_help_text(is_admin: bool) -> str:
    """Build the help screen."""
    base = (
        f"❓ <b>{BOT_TITLE} Help</b>\n\n"
        "👤 <b>User Commands</b>\n"
        "<code>/start</code> — Open the dashboard\n"
        "<code>/help</code> — Show this help screen\n"
        "<code>/status</code> — Show your account status\n"
        "<code>/plan</code> — Show current plan details\n"
        "<code>/tasks</code> — Show what the bot can do\n"
        "<code>/cancel</code> — Cancel the active rename flow\n\n"
        "📦 <b>Archive Actions</b>\n"
        "Send a ZIP or RAR file to extract it, then upload single files, "
        "upload all files, or create a renamed ZIP."
    )
    if not is_admin:
        return base
    return (
        f"{base}\n\n"
        "🛡️ <b>Admin Commands</b>\n"
        "<code>/admin</code> — Show the admin dashboard\n"
        "<code>/stats</code> — Show bot statistics\n"
        "<code>/addpremium USER_ID</code> — Grant premium\n"
        "<code>/removepremium USER_ID</code> — Remove premium\n"
        "<code>/ban USER_ID</code> — Ban a user\n"
        "<code>/unban USER_ID</code> — Unban a user\n"
        "<code>/broadcast MESSAGE</code> — Send a message to all active users"
    )


def build_plan_text(user_row) -> str:
    """Build the plan screen for a user."""
    current_plan = plan_badge(user_row)
    archive_limit = "2 GB" if user_row["is_premium"] else "1 GB"
    if user_row["is_premium"]:
        perks = (
            "✅ Priority transfer lane is active\n"
            "✅ Faster download chunks\n"
            "✅ Concurrent uploads enabled"
        )
    else:
        perks = (
            "📌 You are on the free tier right now.\n"
            "💎 Premium unlocks a faster transfer lane with bigger chunks and concurrent uploads."
        )
    premium_since = _safe(user_row['premium_since']) if user_row['premium_since'] else 'Not active'
    return (
        "💎 <b>Plan Center</b>\n\n"
        f"<b>Current Plan:</b> {current_plan}\n"
        f"<b>Archive Limit:</b> {archive_limit}\n"
        f"<b>Premium Since:</b> {premium_since}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Plan Features</b>\n{perks}"
    )


def build_status_text(user_row, is_admin: bool) -> str:
    """Build the user status panel."""
    role = "🛡️ Admin" if is_admin else "👤 User"
    return (
        "📊 <b>Account Status</b>\n\n"
        f"<b>Name:</b> {_safe(user_row['first_name'])}\n"
        f"<b>Username:</b> {_safe(user_row['username'])}\n"
        f"<b>User ID:</b> <code>{user_row['user_id']}</code>\n"
        f"<b>Role:</b> {role}\n"
        f"<b>Plan:</b> {plan_badge(user_row)}\n"
        f"<b>Joined:</b> {_safe(user_row['joined_at'])}\n"
        f"<b>Last Seen:</b> {_safe(user_row['last_seen_at'])}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📈 <b>Usage Stats</b>\n"
        f"Archives processed: <code>{user_row['archives_processed']}</code>\n"
        f"Files uploaded: <code>{user_row['files_uploaded']}</code>\n"
        f"ZIP exports: <code>{user_row['zip_exports']}</code>\n"
        f"Last archive: <code>{_safe(user_row['last_archive_name'])}</code>"
    )


def build_tasks_text(user_row) -> str:
    """Build the task/features panel."""
    premium_hint = (
        "⭐ Your premium flag is active — fast transfer lane is enabled!"
        if user_row["is_premium"]
        else "💡 Premium plans unlock faster transfers, bigger chunks, and concurrent uploads."
    )
    return (
        "📋 <b>Task Board</b>\n\n"
        "📦 <b>What You Can Do</b>\n\n"
        "1️⃣ Upload ZIP or RAR archives.\n"
        "2️⃣ Inspect file lists with pagination.\n"
        "3️⃣ Upload one file or the full extracted set with live progress.\n"
        "4️⃣ Rename extracted files and rebuild a ZIP.\n"
        "5️⃣ Track your plan, status, and transfer mode from the dashboard.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 <b>Premium</b>\n{premium_hint}"
    )


def build_admin_panel_text(stats_row) -> str:
    """Build the admin panel summary."""
    return (
        "🛡️ <b>Admin Panel</b>\n\n"
        "📈 <b>Global Stats</b>\n"
        f"👥 Users: <code>{stats_row['total_users'] or 0}</code>\n"
        f"⭐ Premium: <code>{stats_row['premium_users'] or 0}</code>\n"
        f"🚫 Banned: <code>{stats_row['banned_users'] or 0}</code>\n"
        f"📦 Archives processed: <code>{stats_row['archives_processed'] or 0}</code>\n"
        f"📤 Files uploaded: <code>{stats_row['files_uploaded'] or 0}</code>\n"
        f"📥 ZIP exports: <code>{stats_row['zip_exports'] or 0}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚙️ <b>Admin Commands</b>\n"
        "<code>/addpremium USER_ID</code>\n"
        "<code>/removepremium USER_ID</code>\n"
        "<code>/ban USER_ID</code>\n"
        "<code>/unban USER_ID</code>\n"
        "<code>/broadcast MESSAGE</code>\n"
        "<code>/stats</code>"
    )


def build_banned_text() -> str:
    """Build the blocked account message."""
    return (
        "🚫 <b>Access Blocked</b>\n\n"
        "Your account is currently banned from using this bot.\n"
        "Contact the bot administrator if you think this is a mistake."
    )


def build_archive_overview_text(archive_name: str, file_count: int, total_size: str) -> str:
    """Build the archive overview message."""
    return (
        "📦 <b>Archive Overview</b>\n\n"
        f"<b>Name:</b> <code>{_safe(archive_name)}</code>\n"
        f"<b>Files:</b> {file_count} files found\n"
        f"<b>Total Size:</b> {total_size}\n\n"
        "Choose an action below. ⬇️"
    )
