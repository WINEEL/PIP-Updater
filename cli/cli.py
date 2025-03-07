import argparse
from main import PipUpdate

def cli():
    parser = argparse.ArgumentParser(description="PIP Updater CLI")
    parser.add_argument("--dry-run", action="store_true", help="Simulate the update process without making changes")

    args = parser.parse_args()
    updater = PipUpdate(dry_run=args.dry_run)
    updater.run()

if __name__ == "__main__":
    cli()
