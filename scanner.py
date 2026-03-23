import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

@dataclass
class ScanResult:
    name: str
    size: int
    count: int
    files: List[Path]

# Expanded Windows junk locations
WINDOWS_TARGETS = {
    "Temp Files": [
        Path(os.environ.get('TEMP', '')),
        Path(os.environ.get('SystemRoot', 'C:\\Windows')) / "Temp",
        Path.home() / "AppData" / "Local" / "Temp"
    ],
    "Prefetch": [
        Path(os.environ.get('SystemRoot', 'C:\\Windows')) / "Prefetch"
    ],
    "ErrorLogs": [
        Path(os.environ.get('SystemRoot', 'C:\\Windows')) / "Logs",
        Path("C:\\ProgramData\\Microsoft\\Windows\\WER") # Windows Error Reporting
    ],
    "Windows Update": [
        Path(os.environ.get('SystemRoot', 'C:\\Windows')) / "SoftwareDistribution" / "Download"
    ],
    "UserCache": [
        Path(os.environ.get('LOCALAPPDATA', '')) / "Microsoft" / "Windows" / "INetCache",
        Path(os.environ.get('LOCALAPPDATA', '')) / "Microsoft" / "Windows" / "WebCache"
    ]
}

DEV_ARTIFACT_NAMES = {"node_modules", "bin", "obj", ".venv", "venv", "__pycache__", ".next", ".cache"}

class SmartScanner:
    def __init__(self, stale_threshold_days: int = 30):
        self.stale_threshold_days = stale_threshold_days
        self.executor = ThreadPoolExecutor(max_workers=os.cpu_count() or 4)

    def scan(self, deep: bool = False, target_path: Optional[Path] = None) -> List[ScanResult]:
        """Runs all discovery functions and returns a list of ScanResult objects."""
        results = []
        
        if target_path:
            target_path = Path(target_path).resolve()
            if not target_path.exists():
                return results

            # Local folder analytics
            future_dev = self.executor.submit(self.find_dev_artifacts, target_path)
            future_junk = self.executor.submit(self.find_generic_junk, target_path)
            
            dev_size, dev_paths = future_dev.result()
            if dev_size > 0:
                results.append(ScanResult("Local Artifacts", dev_size, len(dev_paths), dev_paths))
            
            junk_size, junk_paths = future_junk.result()
            if junk_size > 0:
                results.append(ScanResult("Local Junk", junk_size, len(junk_paths), junk_paths))
            
            return results

        # Parallelize system category scanning
        futures = {}
        for name, paths in WINDOWS_TARGETS.items():
            futures[name] = self.executor.submit(self._scan_category, paths)

        # Non-parallel targets (browser/recycle bin)
        browser_future = self.executor.submit(self.find_browser_caches)
        recycle_future = self.executor.submit(self.find_recycle_bin)

        # Collect system hits
        for name, future in futures.items():
            size, files = future.result()
            if size > 0:
                results.append(ScanResult(name, size, len(files), files))

        # Collect browser/recycle
        b_size, b_files = browser_future.result()
        if b_size > 0:
            results.append(ScanResult("Browser Cache", b_size, len(b_files), b_files))

        r_size, r_files = recycle_future.result()
        if r_size > 0:
            results.append(ScanResult("Recycle Bin", r_size, len(r_files), r_files))

        # Deep Scan (Stale Dev Artifacts)
        if deep:
            dev_roots = [
                Path.home() / "Documents",
                Path.home() / "Desktop",
                Path.home() / "source",
                Path.home() / "Projects"
            ]
            total_dev_size = 0
            total_dev_files = []
            
            dev_futures = [self.executor.submit(self.find_dev_artifacts, root) for root in dev_roots if root.exists()]
            for dfu in dev_futures:
                size, files = dfu.result()
                total_dev_size += size
                total_dev_files.extend(files)
            
            if total_dev_size > 0:
                results.append(ScanResult("Stale Dev Artifacts", total_dev_size, len(total_dev_files), total_dev_files))

        return results

    def _scan_category(self, paths: List[Path]) -> Tuple[int, List[Path]]:
        """Helper for parallel category scanning."""
        combined_size = 0
        combined_files = []
        for path in paths:
            if path.exists():
                size, files = self._analyze_path(path)
                combined_size += size
                combined_files.extend(files)
        return combined_size, combined_files

    def _analyze_path(self, path: Path) -> Tuple[int, List[Path]]:
        """Analyzes a directory to identify deletable files."""
        total_size = 0
        deletable_files = []
        try:
            for root, dirs, files in os.walk(path):
                for f in files:
                    file_path = Path(root) / f
                    try:
                        total_size += file_path.stat().st_size
                        deletable_files.append(file_path)
                    except (PermissionError, FileNotFoundError):
                        continue
        except Exception:
            pass
        return total_size, deletable_files

    def find_browser_caches(self) -> Tuple[int, List[Path]]:
        """Finds cache directories for Chrome, Edge, and Firefox."""
        total_size = 0
        cache_files = []
        appdata = Path(os.environ.get('LOCALAPPDATA', ''))
        
        cache_paths = [
            appdata / "Google" / "Chrome" / "User Data" / "Default" / "Cache",
            appdata / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache",
            Path(os.environ.get('APPDATA', '')) / "Mozilla" / "Firefox" / "Profiles"
        ]
        
        for p in cache_paths:
            if p.exists():
                size, files = self._analyze_path(p)
                total_size += size
                cache_files.extend(files)
        
        return total_size, cache_files

    def find_recycle_bin(self) -> Tuple[int, List[Path]]:
        """Scans the Windows Recycle Bin."""
        total_size = 0
        bin_files = []
        recycle_path = Path("C:\\$Recycle.Bin")
        if recycle_path.exists():
            size, files = self._analyze_path(recycle_path)
            total_size += size
            bin_files.extend(files)
        return total_size, bin_files

    def find_dev_artifacts(self, base_path: Path) -> Tuple[int, List[Path]]:
        """Finds stale developer artifacts in specific directories."""
        total_size = 0
        artifact_list = []
        stale_date = datetime.now() - timedelta(days=self.stale_threshold_days)
        
        try:
            for root, dirs, files in os.walk(base_path, topdown=True):
                matched_dirs = set(dirs) & DEV_ARTIFACT_NAMES
                for d in matched_dirs:
                    dir_path = Path(root) / d
                    try:
                        stat_info = dir_path.stat()
                        last_modified = datetime.fromtimestamp(stat_info.st_mtime)
                        
                        if last_modified < stale_date:
                            try:
                                # Quick size check
                                dir_size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
                                if dir_size > 0:
                                    total_size += dir_size
                                    artifact_list.append(dir_path)
                            except (PermissionError, FileNotFoundError):
                                pass
                    except Exception:
                        continue
                
                # Prune tree: don't recurse into found artifacts
                for d in matched_dirs:
                    if d in dirs:
                        dirs.remove(d)
        except Exception:
            pass
        return total_size, artifact_list

    def find_generic_junk(self, root_path: Path) -> Tuple[int, List[Path]]:
        """Finds common junk patterns (logs, temp files) in any folder."""
        total_size = 0
        junk_paths = []
        junk_extensions = {".log", ".tmp", ".temp", ".bak", ".old"}
        
        try:
            for root, dirs, files in os.walk(root_path):
                for f in files:
                    file_path = Path(root) / f
                    if file_path.suffix.lower() in junk_extensions:
                        try:
                            total_size += file_path.stat().st_size
                            junk_paths.append(file_path)
                        except (PermissionError, FileNotFoundError):
                            continue
        except Exception:
            pass
        return total_size, junk_paths

    def find_large_files(self, base_path: Path, min_size_mb: int = 100) -> List[Tuple[Path, int]]:
        """Discovers files larger than the specified threshold."""
        large_files = []
        min_bytes = min_size_mb * 1024 * 1024
        
        try:
            for root, dirs, files in os.walk(base_path):
                for f in files:
                    file_path = Path(root) / f
                    try:
                        size = file_path.stat().st_size
                        if size >= min_bytes:
                            large_files.append((file_path, size))
                    except (PermissionError, FileNotFoundError):
                        continue
        except Exception:
            pass
        return sorted(large_files, key=lambda x: x[1], reverse=True)
