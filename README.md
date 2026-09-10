# PIP-Updater

PIP-Updater is a small Python learning project and command-line utility. It
discovers packages installed in a selected Python environment and asks `pip` to
upgrade supported packages.

The project began as an early experiment in both Python automation and software
distribution: command-line programs, subprocesses, logging, argument parsing,
icons, PyInstaller, Windows executables, GitHub Actions artifacts, and release
concepts. It was revisited in 2026 as a maintenance and reliability exercise.
The current version is still the original project, later corrected and hardened
rather than rewritten or presented as something it was not.


## Safety

Normal mode bulk-upgrades `pip` and supported packages in the selected Python
environment. Bulk upgrades can break dependency compatibility, so run
`--dry-run` first and use an environment you are comfortable modifying.

This utility is not a replacement for project-specific dependency management,
lock files, or carefully managed virtual environments.


## Features

- Upgrades `pip` for the selected Python interpreter.
- Discovers installed packages with `pip freeze`.
- Passes supported pinned package entries back to `pip` for upgrade.
- Provides a read-only `--dry-run` discovery mode.
- Uses automatically cleaned temporary storage for the upgrade list.
- Reports failures with a nonzero exit status and logs command activity.
- Supports explicit Python-interpreter selection in source and packaged modes.


## Requirements

- Python 3.8 or newer when running from source.
- A working `pip` installation in the target Python environment.

The application itself uses only Python's standard library and its own local
code. PyInstaller is build tooling, not an application runtime dependency.


## Usage

### Running from source

Without `--python`, source mode targets the same Python interpreter used to
launch PIP-Updater. Use `--python` to select another interpreter explicitly.

macOS / Linux:

```bash
python3 main.py
python3 main.py --dry-run
python3 main.py --python /path/to/python --dry-run
```

Windows:

```powershell
py main.py
py main.py --dry-run
py main.py --python "C:\path\to\python.exe" --dry-run
```

`python` may also work where it resolves to Python 3. The secondary entry point,
`cli/cli.py`, delegates to the same application.

Commands and failures are recorded in `pip_updater.log` in the current working
directory. Editable installs and direct-reference entries reported by
`pip freeze` are skipped with a warning because they cannot be safely converted
into ordinary package upgrade arguments.

### Running a packaged executable

Packaged mode requires `--python`. It will not guess which installed Python
environment should be modified.

A PyInstaller-frozen executable contains an embedded runtime used to run the
application itself. That runtime is not the user's target Python environment,
so the intended interpreter must be supplied explicitly and is validated before
any pip operation.

Windows dry-run example:

```powershell
PIP-Updater.exe --python "C:\path\to\python.exe" --dry-run
```

macOS / Linux dry-run example:

```bash
./PIP-Updater --python /path/to/python --dry-run
```


## Testing

The regression suite contains 32 tests. It uses mocks and temporary locations
and does not perform real package upgrades.

macOS / Linux:

```bash
python3 -B -m unittest discover -s tests -v
```

Windows:

```powershell
py -B -m unittest discover -s tests -v
```


## Native Builds and Distribution

The manual GitHub Actions native-build workflow has successfully verified these
native build and smoke-test targets:

- Windows x64: `PIP-Updater.exe`
- macOS arm64: `PIP-Updater` CLI executable
- Linux x64: `PIP-Updater` CLI executable

In addition, a macOS x86_64 executable was successfully built and smoke-tested
locally. These results verify the listed targets; they are not a claim of
exhaustive compatibility with every operating-system version, machine, or Linux
distribution.

Each GitHub Actions job runs the unit tests and source help checks before using
PyInstaller 6.22.2 as an ephemeral build-only dependency. It then creates a
one-file console executable and verifies:

- packaged `--help` output, including the `--python` option;
- refusal to run packaged update mode without an explicit target interpreter;
- packaged dry-run behavior against an isolated temporary virtual environment;
- unchanged pip version and `pip freeze` output before and after that dry-run.

Windows builds use `static/icon.ico`. macOS and Linux builds are native CLI
executables without an `.exe` suffix. The workflow does not create installers,
application bundles, or signed/notarized distributions.

The binaries are currently available as GitHub Actions artifacts from successful
workflow runs. They have not yet been published as permanent downloads in a
current GitHub Release.


## Project History

### Original project and early learning work

This began as one of the author's early Python projects. The learning goal
included both updating packages and exploring how a Python program could become
software that users download and run normally. The repository therefore
included a Windows `.ico`, PyInstaller executable-distribution experiments, and
an early Windows GitHub Actions build-artifact attempt alongside work with CLI
design, subprocesses, logging, and argument parsing.

Later historical changes moved package commands toward `sys.executable`. That
improved ordinary source execution, but it was unsafe for a frozen build because
`sys.executable` identifies the PIP-Updater executable itself in that context.
The early executable implementation should not be read as having been fully
working or cross-platform verified.

### 2026 Reboot maintenance

The project was revisited in 2026 without discarding its original history. The
maintenance work:

- repaired broken dry-run behavior;
- removed unsafe deletion of a fixed temporary directory;
- replaced shell command construction with argument-list subprocess execution;
- improved error reporting and process exit statuses;
- made `pip freeze` entry parsing safer;
- added regression tests and repaired the secondary CLI entry point;
- corrected README and license inconsistencies;
- added explicit `--python` interpreter targeting and safe frozen behavior;
- added Windows, macOS, and Linux subprocess-environment handling;
- added and verified native cross-platform GitHub Actions packaging.

This was a focused effort to make the existing learning project safer and more
reliable, not a claim that the current implementation was present from the
beginning.


## Limitations

- Bulk upgrades can break dependency compatibility.
- Editable and direct-reference `pip freeze` entries may be skipped.
- Packaged mode requires an explicit target Python interpreter.
- There is no GUI or installer.
- Current binaries are workflow artifacts, not current GitHub Release assets.
- macOS binaries are not presented as signed or notarized distributions.
- Compatibility is verified only for the listed build targets, not every
  machine, operating-system version, or Linux distribution.


## License

PIP-Updater is available under the standard MIT License. See `LICENSE`.


## Author

[Wineel Wilson Dasari](https://github.com/wineel10)
