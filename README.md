# PIP Updater - Automate Python Package Updates

PIP Updater is a simple tool to update Python and all installed packages automatically.

## Features
- Updates `pip` to the latest version.
- Upgrades all installed Python packages.
- Supports `--dry-run` mode to simulate updates.
- Cross-platform (Windows, macOS, Linux).

## Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/WINEEL/PIP-Updater.git
   cd PIP-Updater
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
To update all packages, run:
```bash
python main.py
```
To simulate updates (without making changes):
```bash
python main.py --dry-run
```

## Build .exe (Windows Only)
To create a standalone `.exe` file:
```bash
pyinstaller --onefile --name PIP-Updater main.py
```

## License
This project is licensed under the MIT License.
