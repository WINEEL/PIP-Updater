import sys
import shlex
import logging
import argparse
import tempfile
import subprocess

from pathlib import Path
from application.filterpip import filterpip


class PipUpdateError(RuntimeError):
    """Raised when the update process cannot complete safely."""


class PipUpdate:
    def __init__(self, dry_run=False, python_cmd=None):
        self.dry_run = dry_run

        if python_cmd is None and getattr(sys, "frozen", False):
            raise PipUpdateError(
                "This executable cannot safely determine which Python environment "
                "to update. Run main.py with the Python interpreter you want to update."
            )

        self.python_cmd = python_cmd or sys.executable

    def run_command(self, command):
        """Run an argument list without a shell and return the completed process."""
        logging.info("Running: %s", shlex.join(command))

        try:
            return subprocess.run(
                command,
                shell=False,
                check=True,
                capture_output=True,
                text=True,
            )
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
        print("Updating pip...")
        self.run_command(
            [self.python_cmd, "-m", "pip", "install", "--upgrade", "pip"]
        )

    def get_installed_packages(self):
        print("Retrieving installed packages...")
        result = self.run_command([self.python_cmd, "-m", "pip", "freeze"])
        return filterpip(result.stdout)

    def update_packages(self, requirements_file):
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
    args = parser.parse_args(argv)

    configure_logging()
    try:
        PipUpdate(dry_run=args.dry_run).run()
    except PipUpdateError as error:
        logging.error("Update failed: %s", error)
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
