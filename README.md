# TrackMint Personal Finance Desktop

Offline-first personal finance desktop app built with Python, Tkinter, SQLite, local PIN login, Fernet-encrypted local backups, OCR, analytics, and PDF reports.

## Security Model

- Local PIN login is optional and can be enabled from the Admin panel.
- The PIN is never stored directly. TrackMint stores a salted PBKDF2 hash in the local SQLite settings table.
- Runtime databases, audit logs, encrypted key material, and backups stay on the user's machine.
- Backups are encrypted `.enc` files and can be restored only by the same local encryption key.
- Categories can be added, edited, and removed from the Admin panel.

## Core Ledger Behavior

- Cash and online account balances are calculated automatically from transactions and balance transfers.
- Online accounts can represent separate bank accounts, such as `HDFC Bank`, `SBI Bank`, or `ICICI Savings`.
- The Admin panel lets users add, edit, and delete accounts.
- The Balance workspace lets users move funds between any two accounts without changing total wealth.
- Balance transfers are audit-logged and do not count as income or expense.
- Transactions remain month-wise, with Cash Net and total Online Net shown for the selected month.

## Run

```powershell
pip install -r requirements.txt
python -m finance_app.main
```

PIN protection is off unless enabled in the Admin panel. Use a 4 to 8 digit PIN when enabling it.

OCR requires Tesseract installed on the system and available on `PATH`. If OCR is unavailable or parsing fails, the app opens a manual transaction fallback instead of crashing.

## Offline Backup And Restore

Use the top command bar:

- `Backup` creates an encrypted `.enc` backup wherever you choose.
- `Restore` decrypts and validates a selected `.enc` backup before replacing `finance.db`.

Invalid or corrupted backups are rejected safely.

## Databases

Runtime data is stored outside the code package in the local application data directory:

- `finance.db`
- `audit_logs.db`
- encrypted user key material
- encrypted local backups, when saved to the default app backup folder

## Build Executables

Build on the target operating system. PyInstaller does not reliably cross-compile Windows executables from Linux or Linux executables from Windows.

### Windows `.exe`

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-build.txt
python build.py
```

The executable will be created at:

```text
dist\TrackMint.exe
```

### Linux executable

Install Tkinter and Tesseract first:

```bash
sudo apt update
sudo apt install -y python3-tk tesseract-ocr
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-build.txt
python build.py
```

The executable will be created at:

```text
dist/TrackMint
```

### Runtime Notes

- Build Windows on Windows and Linux on Linux.
- OCR needs the Tesseract binary installed on the user's machine and available on `PATH`.
- Runtime databases, audit logs, PIN hash metadata, and encrypted key material are stored in the user's local app-data directory, not inside the executable.
