# PIP-Updater

PIP-Updater is a small Python learning project and command-line utility. It
discovers packages installed in the active Python environment and asks `pip` to
upgrade supported packages. The original project also explored making Python
programs feel like downloadable software through icons, PyInstaller, build
artifacts, and GitHub releases.

The current version preserves that learning history while applying a focused
maintenance repair to its command execution, dry-run behavior, temporary-file
handling, and error reporting.

## Safety

The normal command bulk-upgrades packages in the Python environment used to
launch it. That can create dependency incompatibilities, so use it only in an
environment you are comfortable modifying.

## Features

- Upgrades `pip` for the active source Python interpreter.
- Discovers installed packages with `pip freeze`.
- Passes supported pinned package entries back to `pip` for upgrade.
- Provides a read-only `--dry-run` package-discovery mode.
- Uses automatically cleaned temporary storage for the upgrade list.
- Reports failures with a nonzero exit status and logs command activity.

## Requirements

- Python 3.8 or newer.
- `pip` available for the Python interpreter used to run the project.

Designed for Python 3 on Windows, macOS, and Linux; full cross-platform
integration has not been comprehensively verified.

The application imports only Python standard-library modules and its own local
code. PyInstaller is optional build-time tooling associated with the historical
executable experiment; it is not a runtime dependency.

## Usage

The commands below run the normal updater, perform read-only discovery with
`--dry-run`, and invoke the same application through the thin CLI wrapper.

### macOS / Linux

```bash
python3 main.py
python3 main.py --dry-run
python3 cli/cli.py
```

### Windows

```powershell
py main.py
py main.py --dry-run
py cli/cli.py
```

`python` may also work on systems where it resolves to Python 3.

Commands and failures are recorded in `pip_updater.log` in the current working
directory. Unsupported editable installs and direct-reference entries reported
by `pip freeze` are skipped with a warning.

## Testing

The regression suite uses mocks and temporary locations; it does not perform
real package upgrades.

macOS / Linux:

```bash
python3 -B -m unittest discover -s tests -v
```

Windows:

```powershell
py -B -m unittest discover -s tests -v
```

## Executable experiment

The original repository history includes experimentation with a Windows
PyInstaller build workflow and artifact/release configuration. The icon remains
in `static/icon.ico` as part of that history.

Frozen executable package updating is currently unsupported. In a PyInstaller
application, `sys.executable` identifies the bundled executable rather than a
target Python interpreter. The current code detects that situation and exits
with an actionable error instead of recursively launching the bundle as
`python -m pip`. A build command is intentionally not presented as a supported
updater workflow.

## Limitations

- Bulk upgrades can affect dependency compatibility.
- Editable and direct-reference freeze entries are skipped.
- Frozen executable package updating is not implemented.
- Real package-environment behavior is not comprehensively verified.

## License

PIP-Updater is available under the standard MIT License. See `LICENSE`.

## Author

[Wineel Wilson Dasari](https://github.com/wineel10)
