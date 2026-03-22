"""
Temp File Cleanup Utility
"""

import os
import shutil
from pathlib import Path


class TempCleaner:
    """Handles cleanup of temporary files"""
    
    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
    
    def get_user_temp_dir(self, user_id: int) -> str:
        """Get user's temporary directory path"""
        return os.path.join(self.temp_dir, f"bot_{user_id}")
    
    def create_user_temp_dir(self, user_id: int) -> str:
        """Create and return user's temporary directory"""
        user_dir = self.get_user_temp_dir(user_id)
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def cleanup_user_temp(self, user_id: int) -> bool:
        """Clean up all temporary files for a user"""
        user_dir = self.get_user_temp_dir(user_id)
        try:
            if os.path.exists(user_dir):
                shutil.rmtree(user_dir)
            return True
        except Exception as e:
            print(f"Cleanup error for user {user_id}: {e}")
            return False
    
    def cleanup_file(self, file_path: str) -> bool:
        """Remove a specific file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception as e:
            print(f"File cleanup error: {e}")
            return False
    
    def cleanup_directory(self, dir_path: str) -> bool:
        """Remove a specific directory"""
        try:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
            return True
        except Exception as e:
            print(f"Directory cleanup error: {e}")
            return False
    
    def list_temp_files(self, user_id: int) -> list:
        """List all temporary files for a user"""
        user_dir = self.get_user_temp_dir(user_id)
        if not os.path.exists(user_dir):
            return []
        
        files = []
        for root, dirs, filenames in os.walk(user_dir):
            for filename in filenames:
                files.append(os.path.join(root, filename))
        return files
