"""
ZIP/RAR File Extractor Utility
"""

import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Tuple

try:
    import rarfile
except ImportError:
    rarfile = None


class ArchiveExtractor:
    """Handles extraction of ZIP and RAR archives."""

    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir

    def get_extract_path(self, user_id: int, archive_name: str) -> str:
        """Generate a unique extraction path for a user."""
        safe_name = Path(archive_name).stem
        extract_path = os.path.join(self.temp_dir, f"bot_{user_id}", safe_name)
        os.makedirs(extract_path, exist_ok=True)
        return extract_path

    def extract_zip(self, file_path: str, extract_to: str) -> bool:
        """Extract a ZIP file after validating each member path."""
        try:
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                for member in zip_ref.infolist():
                    destination = self._resolve_member_path(extract_to, member.filename)
                    if destination is None:
                        raise ValueError(f"Unsafe ZIP entry detected: {member.filename}")

                    if member.is_dir():
                        os.makedirs(destination, exist_ok=True)
                        continue

                    os.makedirs(os.path.dirname(destination), exist_ok=True)
                    with zip_ref.open(member, "r") as source, open(destination, "wb") as target:
                        shutil.copyfileobj(source, target)
            return True
        except Exception as exc:
            print(f"ZIP extraction error: {exc}")
            return False

    def extract_rar(self, file_path: str, extract_to: str) -> bool:
        """Extract a RAR file using rarfile when available."""
        if rarfile is None:
            print("RAR extraction error: rarfile is not installed")
            return False

        try:
            with rarfile.RarFile(file_path, "r") as rar_ref:
                for member in rar_ref.infolist():
                    destination = self._resolve_member_path(extract_to, member.filename)
                    if destination is None:
                        raise ValueError(f"Unsafe RAR entry detected: {member.filename}")

                    if member.isdir():
                        os.makedirs(destination, exist_ok=True)
                        continue

                    os.makedirs(os.path.dirname(destination), exist_ok=True)
                    with rar_ref.open(member) as source, open(destination, "wb") as target:
                        shutil.copyfileobj(source, target)
            return True
        except Exception as exc:
            print(f"RAR extraction error: {exc}")
            return False

    def extract_archive(
        self,
        file_path: str,
        user_id: int,
        archive_name: str,
    ) -> Tuple[bool, str, List[str]]:
        """
        Extract an archive and return status, extract path, and file list.
        """
        extract_to = self.get_extract_path(user_id, archive_name)

        if file_path.lower().endswith(".zip"):
            success = self.extract_zip(file_path, extract_to)
        elif file_path.lower().endswith(".rar"):
            success = self.extract_rar(file_path, extract_to)
        else:
            return False, extract_to, []

        if not success:
            return False, extract_to, []

        file_list = self.get_file_list(extract_to)
        return True, extract_to, file_list

    def get_file_list(self, directory: str) -> List[str]:
        """Get a list of all files in a directory recursively."""
        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, directory)
                files.append(rel_path)
        return sorted(files)

    def get_file_info(self, extract_path: str, file_list: List[str]) -> Tuple[int, str]:
        """Return total file count and formatted size."""
        total_size = 0
        count = len(file_list)

        for file_path in file_list:
            full_path = os.path.join(extract_path, file_path)
            if os.path.exists(full_path):
                total_size += os.path.getsize(full_path)

        return count, self.format_size(total_size)

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Format bytes to a human-readable string."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def get_full_path(self, extract_path: str, relative_path: str) -> str:
        """Get the full path from a relative path."""
        return os.path.join(extract_path, relative_path)

    @staticmethod
    def _resolve_member_path(base_dir: str, member_name: str) -> str | None:
        """Resolve an archive member and reject path traversal attempts."""
        normalized_name = member_name.replace("\\", "/").strip("/")
        if not normalized_name:
            return None

        base_path = Path(base_dir).resolve()
        destination = (base_path / normalized_name).resolve()

        try:
            destination.relative_to(base_path)
        except ValueError:
            return None

        return str(destination)
