import re
import sys


PINNED_PACKAGE = re.compile(
    r"^([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)={2,3}[^=].*$"
)


def filterpip(freeze_output):
    """Return package names from supported pinned pip freeze entries."""
    packages = []

    for raw_line in freeze_output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        match = PINNED_PACKAGE.fullmatch(line)
        if match:
            packages.append(match.group(1))
        else:
            print(
                "Warning: skipping an unsupported package entry.",
                file=sys.stderr,
            )

    return packages
