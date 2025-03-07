import argparse
import os
import shutil
import subprocess
import logging
from time import sleep

from application.filterpip import filterpip

# Logging setup
logging.basicConfig(filename="pip_updater.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class PipUpdate:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.data_dir = "datap_"

    def run_command(self, command):
        """Executes a shell command with error handling."""
        try:
            logging.info(f"Running: {command}")
            if not self.dry_run:
                subprocess.run(command, shell=True, check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error running command: {command} -> {e}")
            print(f"Error: {e}")

    def update_pip(self):
        """Updates pip to the latest version."""
        print("Updating pip...")
        self.run_command("python -m pip install --upgrade pip")

    def create_data_dir(self):
        """Creates a hidden directory for storing temp files."""
        if os.path.exists(self.data_dir):
            shutil.rmtree(self.data_dir)
        os.makedirs(self.data_dir)
        if os.name == "nt":
            self.run_command(f"attrib +h {self.data_dir}")  # Hide folder on Windows

    def get_installed_packages(self):
        """Gets the list of installed packages."""
        print("Retrieving installed packages...")
        self.run_command(f"pip freeze > {self.data_dir}/old.txt")

    def update_packages(self):
        """Updates all installed packages."""
        print("Updating all installed packages...")
        filterpip()  # Filter the list
        self.run_command(f"pip install --upgrade -r {self.data_dir}/new.txt")

    def cleanup(self):
        """Cleans up temp files."""
        shutil.rmtree(self.data_dir, ignore_errors=True)

    def run(self):
        """Runs the full update process."""
        self.update_pip()
        self.create_data_dir()
        self.get_installed_packages()
        self.update_packages()
        self.cleanup()
        print("Successfully updated all packages!")

def main():
    parser = argparse.ArgumentParser(description="PIP Updater - A CLI Tool to Update Python Packages")
    parser.add_argument("--dry-run", action="store_true", help="Simulate the update process without making changes")
    
    args = parser.parse_args()
    
    updater = PipUpdate(dry_run=args.dry_run)
    updater.run()

if __name__ == "__main__":
    main()
