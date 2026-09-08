import sys

from pathlib import Path


# Allow the documented ``python cli/cli.py`` invocation to find root main.py.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import main as application_main


def cli():
    return application_main()


if __name__ == "__main__":
    raise SystemExit(cli())
