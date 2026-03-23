import os
import shutil
import random
from pathlib import Path
from typing import List, Tuple

class SafeCleaner:
    def __init__(self, dry_run: bool = False, secure: bool = False):
        self.dry_run = dry_run
        self.secure = secure

    def delete_files(self, file_paths: List[Path]) -> Tuple[int, int]:
        """Deletes a list of files or directories safely. Returns (success_count, fail_count)."""
        success_count = 0
        fail_count = 0
        
        for path in file_paths:
            if not path.exists():
                continue
                
            try:
                if self.dry_run:
                    success_count += 1
                    continue
                
                if path.is_file():
                    if self.secure:
                        self._secure_overwrite(path)
                    os.remove(path)
                    success_count += 1
                elif path.is_dir():
                    shutil.rmtree(path)
                    success_count += 1
            except (PermissionError, OSError):
                fail_count += 1
                
        return success_count, fail_count

    def _secure_overwrite(self, path: Path):
        """Overwrites file with random data before deletion."""
        try:
            if not path.is_file():
                return
            
            size = path.stat().st_size
            if size > 100 * 1024 * 1024: # Don't shred files > 100MB for performance
                return
                
            with open(path, "ba+", buffering=0) as f:
                # One pass of random data
                f.seek(0)
                f.write(os.urandom(size))
        except Exception:
            pass

    def cleanup_empty_folders(self, base_path: Path):
        """Recursively removes empty subdirectories."""
        if self.dry_run or not base_path.exists() or not base_path.is_dir():
            return

        try:
            for root, dirs, files in os.walk(base_path, topdown=False):
                for d in dirs:
                    dir_path = Path(root) / d
                    try:
                        if not os.listdir(dir_path):
                            os.rmdir(dir_path)
                    except OSError:
                        pass
        except Exception:
            pass
