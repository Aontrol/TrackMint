from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> None:
    data_separator = ";" if os.name == "nt" else ":"

    config_keep = ROOT / "finance_app" / "config" / ".gitkeep"
    add_data = f"{config_keep}{data_separator}finance_app/config"

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

        "--add-data",
        add_data,

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