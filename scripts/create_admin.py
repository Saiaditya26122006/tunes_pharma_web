"""One-time script to create the first admin_users account.

Usage:
    python scripts/create_admin.py

Automatically loads the project's .env file (same approach as the Flask
app). Requires SUPABASE_URL and SUPABASE_SERVICE_KEY to be set there.

The password is read interactively via getpass (never echoed, logged, or
stored in source). The hash uses werkzeug.security.generate_password_hash,
the same mechanism used by auth_service.py for both admin and doctor auth.

Safe to delete this file after the first admin account is created.
"""

import os
import re
import sys
import getpass
from pathlib import Path

def main():
    # ── Load .env from project root ──────────────────────────────
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"

    try:
        from dotenv import load_dotenv
    except ImportError:
        print("Error: python-dotenv not installed. Run: pip install python-dotenv")
        sys.exit(1)

    if env_path.is_file():
        load_dotenv(env_path, override=True)
        print(f"Loaded .env from {env_path}")
    else:
        print(f"Warning: No .env file found at {env_path}")
        print("Falling back to existing environment variables.\n")

    # ── Check Supabase env vars ──────────────────────────────────
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()

    if not url or not key:
        missing = []
        if not url:
            missing.append("SUPABASE_URL")
        if not key:
            missing.append("SUPABASE_SERVICE_KEY")
        print(f"\nError: Missing required environment variable(s): {', '.join(missing)}")
        print(f"Set them in your .env file at: {env_path}")
        sys.exit(1)

    # ── Collect inputs ───────────────────────────────────────────
    print("\n=== Tunes Pharma — Create Admin Account ===\n")

    name = input("Admin name: ").strip()
    if not name:
        print("Error: Name cannot be empty.")
        sys.exit(1)

    email = input("Admin email: ").strip().lower()
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        print("Error: Invalid email address.")
        sys.exit(1)

    password = getpass.getpass("Password (min 8 chars, hidden): ")
    if len(password) < 8:
        print("Error: Password must be at least 8 characters.")
        sys.exit(1)
    if password.isdigit():
        print("Error: Password cannot be all digits.")
        sys.exit(1)
    if password.isalpha():
        print("Error: Password must contain at least one number or special character.")
        sys.exit(1)

    password_confirm = getpass.getpass("Confirm password: ")
    if password != password_confirm:
        print("Error: Passwords do not match.")
        sys.exit(1)

    # ── Connect to Supabase ──────────────────────────────────────
    try:
        from supabase import create_client
    except ImportError:
        print("Error: supabase package not installed. Run: pip install supabase")
        sys.exit(1)

    try:
        sb = create_client(url, key)
    except Exception as e:
        print(f"Error: Could not connect to Supabase: {e}")
        sys.exit(1)

    # ── Check for duplicate email ────────────────────────────────
    try:
        existing = sb.table("admin_users").select("id, email").eq("email", email).execute()
        if existing.data:
            print(f"\nError: An admin account with email '{email}' already exists.")
            sys.exit(1)
    except Exception as e:
        print(f"Error: Could not query admin_users table: {e}")
        print("Have you run the migration (schema.sql) yet?")
        sys.exit(1)

    # ── Hash password and insert ─────────────────────────────────
    from werkzeug.security import generate_password_hash

    password_hash = generate_password_hash(password)

    # Clear password from memory as soon as possible
    del password, password_confirm

    try:
        result = sb.table("admin_users").insert({
            "email": email,
            "password_hash": password_hash,
            "name": name,
            "role": "admin",
            "is_active": True,
        }).execute()
    except Exception as e:
        print(f"\nError: Insert failed: {e}")
        sys.exit(1)

    if not result.data:
        print("\nError: Insert returned no data. Check Supabase logs.")
        sys.exit(1)

    admin = result.data[0]
    print(f"\nAdmin account created successfully.")
    print(f"  ID:    {admin['id']}")
    print(f"  Name:  {admin['name']}")
    print(f"  Email: {admin['email']}")
    print(f"  Role:  {admin['role']}")
    print(f"\nYou can now log in at /admin using this email and password.")
    print("This script can be safely deleted.\n")


if __name__ == "__main__":
    main()
