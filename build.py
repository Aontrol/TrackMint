from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> None:
    icon_path = ROOT / "assets" / "trackmint.ico"

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        "TrackMint",
        "--onefile",
        "--windowed",
        "--clean",

        # APP ICON
        "--icon",
        str(icon_path),

        "--hidden-import",
        "matplotlib.backends.backend_tkagg",

        "--hidden-import",
        "PIL.Image",

        "--hidden-import",
        "pytesseract",

        str(ROOT / "finance_app" / "main.py"),
    ]

    subprocess.run(command, cwd=ROOT, check=True)

    print("Build complete. Output is in the dist directory.")


if __name__ == "__main__":
    main()
