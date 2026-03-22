"""
Transfer formatting and profile helpers.
"""

from __future__ import annotations

from dataclasses import dataclass

from config import (
    FREE_DOWNLOAD_CHUNK_SIZE,
    FREE_UPLOAD_CONCURRENCY,
    PREMIUM_DOWNLOAD_CHUNK_SIZE,
    PREMIUM_UPLOAD_CONCURRENCY,
    PROGRESS_UPDATE_INTERVAL,
    UPLOAD_DELAY,
)


@dataclass(frozen=True)
class TransferProfile:
    """Transfer tuning values for a user tier."""

    name: str
    upload_concurrency: int
    upload_delay: float
    download_chunk_size: int
    progress_interval: float


def get_transfer_profile(is_premium: bool) -> TransferProfile:
    """Return the transfer profile for a user."""
    if is_premium:
        return TransferProfile(
            name="Premium Fast Lane",
            upload_concurrency=PREMIUM_UPLOAD_CONCURRENCY,
            upload_delay=0,
            download_chunk_size=PREMIUM_DOWNLOAD_CHUNK_SIZE,
            progress_interval=PROGRESS_UPDATE_INTERVAL,
        )

    return TransferProfile(
        name="Standard",
        upload_concurrency=FREE_UPLOAD_CONCURRENCY,
        upload_delay=UPLOAD_DELAY,
        download_chunk_size=FREE_DOWNLOAD_CHUNK_SIZE,
        progress_interval=PROGRESS_UPDATE_INTERVAL,
    )


def format_size(size_bytes: int | float) -> str:
    """Format bytes to a human-readable string."""
    value = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} TB"


def format_speed(bytes_per_second: float) -> str:
    """Format a byte rate to a readable speed string."""
    return f"{format_size(bytes_per_second)}/s"


def format_eta(seconds: float | None) -> str:
    """Format seconds remaining into a compact ETA string."""
    if seconds is None or seconds < 0:
        return "--"

    whole = int(seconds)
    hours, remainder = divmod(whole, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def build_progress_bar(current: int | float, total: int | float, width: int = 12) -> str:
    """Build a text progress bar."""
    if total <= 0:
        ratio = 0.0
    else:
        ratio = max(0.0, min(1.0, float(current) / float(total)))

    filled = int(round(ratio * width))
    return "#" * filled + "-" * (width - filled)
