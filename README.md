# PIP-Updater
A cross-platform Python CLI tool that works seamlessly on **macOS, Windows, and Linux** — update `pip` and all your installed packages with a single command.


## Features
- Updates `pip` to the latest version  
- Upgrades all installed Python packages  
- Optional `--dry-run` mode to simulate updates  
- Cross-platform support (tested on Windows & macOS)  
- Automatically cleans up temporary data after run  
- Logs activity in `pip_updater.log`


## Project Structure

```
PIP-Updater/
├── application/
│   └── filterpip.py         # Filters packages from pip freeze
├── cli/
│   └── cli.py               # Alternative CLI entry point
├── main.py                  # Main script (entry point)
├── static/
│   └── icon.ico             # App icon (for packaging, optional)
├── .gitignore               # Git ignored files
├── LICENSE                  # MIT License
├── README.md                # You’re reading it :)
```


## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/WINEEL/PIP-Updater.git
   cd PIP-Updater
   ```

2. **(Optional) Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # macOS/Linux
   # OR
   .\venv\Scripts\activate   # Windows
   ```

3. **Install dependencies:**  
   No additional packages required! This tool works entirely with Python's standard library.


## Usage

To update pip and all installed packages:
```bash
python3 main.py
```

To simulate the update process without making changes:
```bash
python3 main.py --dry-run
```

Alternatively, you can run it from the `cli.py` wrapper:
```bash
python3 cli/cli.py
```


## What It Does Internally

1. Updates `pip` itself using:
   ```bash
   python3 -m pip install --upgrade pip
   ```
2. Generates a list of installed packages via `pip freeze`
3. Filters only package names into a new list
4. Upgrades all packages using:
   ```bash
   python3 -m pip install --upgrade -r new.txt
   ```
5. Deletes temporary data after completion


## Log File
After running the tool, a log file named `pip_updater.log` is automatically created in the root directory.

It records timestamps, commands run, and any errors encountered — useful for debugging or checking what happened during the update.


## License
This project is **open-source** and licensed under the **MIT License**.
Feel free to modify and improve upon it!


## Author  
- **WINEEL WILSON DASARI**  
- wineel10wilson@gmail.com  
- GitHub: [wineel10](https://github.com/wineel10) 


## Tip

Want to turn this into a standalone executable? You can manually use:

```bash
pyinstaller --onefile --name PIP_Updater --icon static/icon.ico main.py
```

A sample icon file (`static/icon.ico`) is already included in the repo. I created it just to complete the structure — feel free to **use, modify, or replace** it as you wish.

> **Note:** PyInstaller works on **Windows, macOS, and Linux**, but you can only build executables **for your current operating system**. Cross-compilation is not supported.

### Platform-specific behavior:

| OS         | Output Format       | Icon Support                      |
|------------|---------------------|-----------------------------------|
| **Windows**| `PIP_Updater.exe`   | `.ico` supported                  |
| **macOS**  | `PIP_Updater` binary| Use `.icns` if building `.app`    |
| **Linux**  | `PIP_Updater` binary| No icon support by default        |

> This project does **not** include an auto-build workflow for `.exe` or `.app`. You can create your own GitHub Actions workflow if needed.
