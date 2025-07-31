#!/usr/bin/env python3
"""
Fix ModuleNotFoundError: from src.export import export_excel

What it does:
- Ensures src/ is a package (creates src/__init__.py if missing).
- Adds a safe sys.path fallback at the top of app.py so "from src..." imports work
  even when the working directory is not the project root (common on some hosts).
- Verifies that src.export and export_excel can be imported.

Usage:
    python fix_imports.py
"""

from pathlib import Path
import shutil
import sys
import re
import importlib.util

PROJECT_ROOT = Path(__file__).resolve().parent
APP_PATH = PROJECT_ROOT / "app.py"
SRC_DIR = PROJECT_ROOT / "src"
INIT_PATH = SRC_DIR / "__init__.py"

PATCH_BEGIN = "# --- BEGIN: path safety patch (added by fix_imports.py) ---"
PATCH_END = "# --- END: path safety patch (added by fix_imports.py) ---"
PATCH_BLOCK = f"""{PATCH_BEGIN}
import sys as _sys, os as _os
# Ensure the project root is on sys.path for 'from src...' imports
_pr = _os.path.dirname(__file__)
if _pr not in _sys.path:
    _sys.path.append(_pr)
{PATCH_END}
"""

def ensure_src_package():
    if not SRC_DIR.exists():
        raise SystemExit(f"[ERROR] Expected folder not found: {SRC_DIR}. "
                         "Run this script from your project root where app.py and src/ live.")
    if not INIT_PATH.exists():
        INIT_PATH.write_text("# make src a package\n", encoding="utf-8")
        print(f"[OK] Created {INIT_PATH}")
    else:
        print(f"[OK] {INIT_PATH} already exists")

def backup_app():
    if not APP_PATH.exists():
        raise SystemExit(f"[ERROR] app.py not found at {APP_PATH}")
    backup = PROJECT_ROOT / "app.py.bak"
    shutil.copy2(APP_PATH, backup)
    print(f"[OK] Backed up app.py -> {backup}")

def needs_patch(app_text: str) -> bool:
    # If the patch markers are present, or any similar path-append already exists, skip.
    if PATCH_BEGIN in app_text and PATCH_END in app_text:
        return False
    # Heuristic: if app already appends __file__ dir, skip
    if re.search(r"sys\.path\.append\(.*__file__.*\)", app_text):
        return False
    return True

def apply_patch_to_app():
    app_text = APP_PATH.read_text(encoding="utf-8")

    if not needs_patch(app_text):
        print("[OK] app.py already has a suitable path patch; no edit needed.")
        return

    # Insert the patch AFTER the first import block to keep things tidy.
    # Find the first line that isn't a comment/blank and comes after initial imports.
    lines = app_text.splitlines()
    insert_idx = 0

    # Strategy: find the end of the initial import cluster at the top
    # We'll scan from top until we hit the first non-import, non-blank, non-comment line.
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            insert_idx = i + 1
            continue
        # allow docstring lines at very top
        if (i == 0 and (stripped.startswith('"""') or stripped.startswith("'''"))):
            # skip until the closing docstring
            end_ds = i + 1
            while end_ds < len(lines):
                if lines[end_ds].strip().endswith('"""') or lines[end_ds].strip().endswith("'''"):
                    insert_idx = end_ds + 1
                    i = end_ds
                    break
                end_ds += 1
            continue
        # allow blanks and comments
        if stripped == "" or stripped.startswith("#"):
            continue
        # first substantive line hit; stop here
        break

    new_text = "\n".join(lines[:insert_idx] + [PATCH_BLOCK] + lines[insert_idx:])
    APP_PATH.write_text(new_text, encoding="utf-8")
    print(f"[OK] Inserted path safety patch into app.py at line {insert_idx+1}")

def verify_import():
    # Add project root to path for this verification run
    pr = str(PROJECT_ROOT)
    if pr not in sys.path:
        sys.path.append(pr)

    # Verify we can import src.export and find export_excel
    spec = importlib.util.find_spec("src.export")
    if spec is None:
        raise SystemExit("[ERROR] Could not find module 'src.export' after fixes.")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    if not hasattr(mod, "export_excel"):
        raise SystemExit("[ERROR] 'src.export' loaded but missing 'export_excel'.")
    print("[OK] Verified: src.export.export_excel is importable.")

def main():
    print(f"[INFO] Project root: {PROJECT_ROOT}")
    ensure_src_package()
    backup_app()
    apply_patch_to_app()
    verify_import()
    print("\n[ALL GOOD] Fix applied. You can now run:")
    print("  streamlit run app.py")

if __name__ == "__main__":
    main()
