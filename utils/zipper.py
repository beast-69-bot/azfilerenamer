"""
ZIP File Creator Utility
"""

import os
import zipfile
from pathlib import Path


class ZipCreator:
    """Handles creation of ZIP archives."""

    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir

    def create_zip(
        self,
        source_dir: str,
        renamed_files: dict[str, str],
        original_archive_name: str,
        user_id: int,
    ) -> str:
        """Create a new ZIP file with renamed files."""
        original_stem = Path(original_archive_name).stem
        output_name = f"{original_stem}_renamed.zip"
        output_dir = os.path.join(self.temp_dir, f"bot_{user_id}")
        output_path = os.path.join(output_dir, output_name)
        os.makedirs(output_dir, exist_ok=True)

        seen_paths: set[str] = set()

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for old_rel_path, new_rel_path in renamed_files.items():
                old_full_path = os.path.join(source_dir, old_rel_path)
                normalized_new_path = new_rel_path.replace("\\", "/").strip("/")
                if not normalized_new_path:
                    raise ValueError("Renamed file path cannot be empty.")

                if normalized_new_path in seen_paths:
                    raise ValueError(f"Duplicate output filename: {normalized_new_path}")

                if not os.path.exists(old_full_path):
                    continue

                seen_paths.add(normalized_new_path)
                zipf.write(old_full_path, normalized_new_path)

        return output_path

    def create_zip_from_directory(self, source_dir: str, output_path: str) -> str:
        """Create a ZIP file from an entire directory."""
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(source_dir):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)

        return output_path

    def get_zip_size(self, zip_path: str) -> str:
        """Get the formatted size of a ZIP file."""
        size_bytes = os.path.getsize(zip_path)
        return self.format_size(size_bytes)

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Format bytes to a human-readable string."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
