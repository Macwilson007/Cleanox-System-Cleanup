# 🤖 Cleanox: Advanced System Cleaner & Optimizer

Cleanox is a high-performance system maintenance CLI built for speed and reliability. It identifies and cleans system junk, stale developer artifacts, and monstrous files consuming your disk space.

## ✨ Features

- **🚀 Parallel Scanning**: Uses multi-threading to scan disk clusters and specific project folders simultaneously.
- **🧹 Smart Deep Analysis**: Finds stale `node_modules`, `.venv`, `bin/obj`, and other heavy-weight dev folders based on access age.
- **🔍 Large File Discovery**: A built-in `large` command to find and list the biggest space-hogs on your machine.
- **🛡️ Secure Shredding**: Optional `--shred` flag that overwrites file content before deletion for security.
- **☁️ DNS Optimization**: Instantly flush your Windows DNS cache for performance.
- **📝 Dry Run Mode**: Safety first—preview deletions before they happen.

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Windows OS (Optimized for Windows maintenance)
- Administrative privileges (recommended for system-wide temp cleaning)

### Installation

```bash
# Clone the repository
git clone https://github.com/USER/Cleanox.git
cd Cleanox

# Install dependencies (use uv or pip)
pip install .
```

## 🛠️ Usage Guide

### 1. Perform a System Scan
Quickly see how much space you can reclaim.
```bash
cleanox scan
```
Add `--deep` for a comprehensive search into developer-specific locations.
```bash
cleanox scan --deep
```

### 2. Clean Up Junk
Free up identified space interactively.
```bash
cleanox clean
```
Skip prompts and clean everything instantly:
```bash
cleanox clean --auto
```

### 3. Find Gigantic Files
Quickly find files larger than N megabytes.
```bash
# Search current folder for files > 100MB
cleanox large .

# Search specific path for files > 500MB
cleanox large C:\Downloads --min-size 500
```

### 4. Optimize Network performance
Flush the local DNS resolution cache:
```bash
cleanox optimize
```

## 🛡️ Commands Reference

| Command | Usage | Description |
|---|---|---|
| `scan` | `cleanox scan [--path] [--deep]` | Analyzes targets for potential savings. |
| `clean` | `cleanox clean [--auto] [--dry-run] [--shred]` | Deletes identified junk categories. |
| `large` | `cleanox large [PATH] [--min-size]` | Lists heavy-weight files in a directory. |
| `optimize` | `cleanox optimize [--dns]` | Performs maintenance tasks (DNS flush). |

---
*Built for efficiency. Reclaim your gigabytes.*
