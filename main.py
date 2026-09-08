import os
import sys
import shlex
import logging
import argparse
import tempfile
import subprocess

from pathlib import Path
from application.filterpip import filterpip


PYTHON_IDENTITY_MARKER = "PIP_UPDATER_PYTHON_IDENTITY_V1"


class PipUpdateError(RuntimeError):
    """Raised when the update process cannot complete safely."""


class PipUpdate:
    def __init__(self, dry_run=False, python_cmd=None):
        self.dry_run = dry_run
        self.frozen = getattr(sys, "frozen", False)

        if python_cmd is None and self.frozen:
            raise PipUpdateError(
                "This executable cannot safely determine which Python environment "
                "to update. Provide the target interpreter with --python PATH."
            )

        if python_cmd is None:
            self.python_cmd = sys.executable
            self.python_validated = True
        else:
            self.python_cmd = os.path.abspath(os.path.expanduser(python_cmd))
            self.python_validated = False

        self.windows_dll_directory_sanitized = False

    def _target_is_frozen_executable(self):
        """Return whether the selected target is the running frozen executable."""
        if not self.frozen:
            return False

        try:
            return os.path.samefile(self.python_cmd, sys.executable)
        except OSError:
            target = os.path.normcase(os.path.realpath(self.python_cmd))
            executable = os.path.normcase(os.path.realpath(sys.executable))
            return target == executable

    @staticmethod
    def _path_is_within(path, root):
        if not path or not root:
            return False

        try:
            path = os.path.normcase(os.path.realpath(path))
            root = os.path.normcase(os.path.realpath(root))
            return os.path.commonpath([path, root]) == root
        except (OSError, ValueError):
            return False

    def _subprocess_environment(self):
        """Return PyInstaller-sanitized environment variables when frozen."""
        if not self.frozen:
            return None

        environment = os.environ.copy()

        if sys.platform == "darwin":
            bundle_root = getattr(sys, "_MEIPASS", None)
            library_path = environment.get("DYLD_LIBRARY_PATH")
            if bundle_root and library_path:
                entries = library_path.split(os.pathsep)
                entries = [
                    entry
                    for entry in entries
                    if not self._path_is_within(entry, bundle_root)
                ]
                if entries:
                    environment["DYLD_LIBRARY_PATH"] = os.pathsep.join(entries)
                else:
                    environment.pop("DYLD_LIBRARY_PATH", None)
        elif sys.platform.startswith("linux"):
            original_library_path = environment.get("LD_LIBRARY_PATH_ORIG")
            if original_library_path is None:
                environment.pop("LD_LIBRARY_PATH", None)
            else:
                environment["LD_LIBRARY_PATH"] = original_library_path
        elif sys.platform != "win32":
            raise PipUpdateError(
                "Packaged execution is supported only on Windows, macOS, and Linux."
            )

        return environment

    @staticmethod
    def _clear_windows_dll_directory():
        """Restore the standard Windows DLL search path for external programs."""
        import ctypes

        if not ctypes.windll.kernel32.SetDllDirectoryW(None):
            raise ctypes.WinError()

    def _prepare_external_process(self):
        if (
            self.frozen
            and sys.platform == "win32"
            and not self.windows_dll_directory_sanitized
        ):
            try:
                self._clear_windows_dll_directory()
            except OSError as error:
                raise PipUpdateError(
                    "Could not safely prepare the Windows environment for the "
                    f"selected Python interpreter: {error}"
                ) from error
            self.windows_dll_directory_sanitized = True

    def validate_python(self):
        """Validate an explicitly selected interpreter before any pip operation."""
        if self.python_validated:
            return

        if self._target_is_frozen_executable():
            raise PipUpdateError(
                "The selected --python path is the PIP-Updater executable, not a "
                "Python interpreter."
            )

        identity_command = [
            self.python_cmd,
            "-I",
            "-c",
            f"print({PYTHON_IDENTITY_MARKER!r})",
        ]
        try:
            result = self.run_command(identity_command)
        except PipUpdateError as error:
            raise PipUpdateError(
                f"The selected --python path failed the Python identity check.\n{error}"
            ) from error

        if result.stdout.strip() != PYTHON_IDENTITY_MARKER:
            raise PipUpdateError(
                "The selected --python path did not identify itself as a compatible "
                "Python interpreter."
            )

        try:
            self.run_command([self.python_cmd, "-m", "pip", "--version"])
        except PipUpdateError as error:
            raise PipUpdateError(
                f"The selected Python interpreter does not provide a working pip.\n{error}"
            ) from error

        self.python_validated = True

    def run_command(self, command):
        """Run an argument list without a shell and return the completed process."""
        logging.info("Running: %s", shlex.join(command))
        self._prepare_external_process()

        run_options = {
            "shell": False,
            "check": True,
            "capture_output": True,
            "text": True,
        }
        environment = self._subprocess_environment()
        if environment is not None:
            run_options["env"] = environment

        try:
            return subprocess.run(command, **run_options)
        except subprocess.CalledProcessError as error:
            detail = (error.stderr or error.stdout or "").strip()
            if len(detail) > 2000:
                detail = detail[-2000:]

            message = (
                f"Command failed with exit code {error.returncode}: "
                f"{shlex.join(command)}"
            )
            if detail:
                message = f"{message}\n{detail}"
            raise PipUpdateError(message) from error
        except OSError as error:
            raise PipUpdateError(
                f"Could not run {shlex.join(command)}: {error}"
            ) from error

    def update_pip(self):
        self.validate_python()
        print("Updating pip...")
        self.run_command(
            [self.python_cmd, "-m", "pip", "install", "--upgrade", "pip"]
        )

    def get_installed_packages(self):
        self.validate_python()
        print("Retrieving installed packages...")
        result = self.run_command([self.python_cmd, "-m", "pip", "freeze"])
        return filterpip(result.stdout)

    def update_packages(self, requirements_file):
        self.validate_python()
        print("Updating all supported installed packages...")
        self.run_command(
            [
                self.python_cmd,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "-r",
                str(requirements_file),
            ]
        )

    def show_dry_run(self, packages):
        print("Dry run: pip would be upgraded.")
        if packages:
            print(
                f"Dry run: {len(packages)} package(s) would be passed to pip "
                "for upgrade:"
            )
            for package in packages:
                print(f"  {package}")
        else:
            print("Dry run: no supported package entries were found.")

    def run(self):
        """Run the update process, propagating any required-operation failure."""
        self.validate_python()

        if not self.dry_run:
            self.update_pip()

        packages = self.get_installed_packages()

        if self.dry_run:
            self.show_dry_run(packages)
            return

        if packages:
            try:
                with tempfile.TemporaryDirectory(prefix="pip-updater-") as temp_dir:
                    requirements_file = Path(temp_dir) / "packages.txt"
                    requirements_file.write_text(
                        "\n".join(packages) + "\n", encoding="utf-8"
                    )
                    self.update_packages(requirements_file)
            except OSError as error:
                raise PipUpdateError(
                    f"Could not use a temporary requirements file: {error}"
                ) from error

        print("Successfully updated pip and all supported packages!")


def configure_logging():
    logging.basicConfig(
        filename="pip_updater.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="PIP Updater - A CLI Tool to Update Python Packages"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show packages that would be passed to pip without installing them",
    )
    parser.add_argument(
        "--python",
        metavar="PATH",
        help=(
            "Python interpreter whose packages should be inspected or updated "
            "(required for a packaged executable)"
        ),
    )
    args = parser.parse_args(argv)

    configure_logging()
    try:
        PipUpdate(dry_run=args.dry_run, python_cmd=args.python).run()
    except PipUpdateError as error:
        logging.error("Update failed: %s", error)
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
