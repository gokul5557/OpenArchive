import asyncio
import asyncpg
import argparse
import sys
import os

# Add parent directory to path to allow importing core
sys.path.append(os.getcwd())

try:
    from core import security
    from core.config import settings
except ImportError:
    print("Error: Could not import core modules. Make sure you are running this from the root directory.")
    sys.exit(1)

async def add_user(username, password, role, org_id):
    DATABASE_URL = settings.DATABASE_URL
    
    print(f"Connecting to database...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return

    try:
        # Check if user exists
        exists = await conn.fetchval("SELECT 1 FROM users WHERE username = $1", username)
        if exists:
            print(f"User '{username}' already exists. Updating...")
            password_hash = security.get_password_hash(password)
            await conn.execute("""
                UPDATE users 
                SET password_hash = $1, role = $2, org_id = $3
                WHERE username = $4
            """, password_hash, role, org_id, username)
            print(f"User '{username}' updated successfully.")
        else:
            print(f"Creating new user '{username}'...")
            password_hash = security.get_password_hash(password)
            await conn.execute("""
                INSERT INTO users (username, password_hash, role, org_id, domains)
                VALUES ($1, $2, $3, $4, '[]')
            """, username, password_hash, role, org_id)
            print(f"User '{username}' created successfully.")

    except Exception as e:
        print(f"Error executing database operation: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add or Update an Admin User")
    parser.add_argument("username", help="Username for the new user")
    parser.add_argument("password", help="Password for the new user")
    parser.add_argument("--role", default="client_admin", choices=["super_admin", "client_admin", "auditor"], help="Role of the user (default: client_admin)")
    parser.add_argument("--org-id", type=int, default=None, help="Organization ID (required for client_admin/auditor)")

    args = parser.parse_args()

    # Validation
    if args.role in ["client_admin", "auditor"] and args.org_id is None:
        print("Error: --org-id is required for client_admin and auditor roles.")
        sys.exit(1)
    
    # If super_admin and no org_id, default to 1 (or whatever default org is)
    if args.role == "super_admin" and args.org_id is None:
        # We'll fetch default later or let it be None if allowed, but schema usually requires it or defaults.
        # Let's assume we want to explicit.
        pass

    asyncio.run(add_user(args.username, args.password, args.role, args.org_id))
