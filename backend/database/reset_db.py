#!/usr/bin/env python3
"""
Database Reset Script
Drops all tables, recreates schema, and loads seed data
"""

import sys
import argparse
from pathlib import Path
from src.client import DataAPIClient
from src.models import Database
from decimal import Decimal

from src.schemas import UserCreate
from src.test_scenarios import DEFAULT_SCENARIO, apply_scenario, list_scenarios


def drop_all_tables(db: DataAPIClient):
    """Drop all tables in correct order (respecting foreign keys)"""
    print("Dropping existing tables...")
    
    # Order matters due to foreign key constraints
    tables_to_drop = [
        'positions',
        'accounts',
        'jobs',
        'instruments',
        'users'
    ]
    
    for table in tables_to_drop:
        try:
            db.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            print(f"   Dropped {table}")
        except Exception as e:
            print(f"   Warning: Error dropping {table}: {e}")
    
    # Also drop the function
    try:
        db.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")
        print(f"   Dropped update_updated_at_column function")
    except Exception as e:
        print(f"   Warning: Error dropping function: {e}")


def create_test_data(db_models: Database, scenario_id: str = DEFAULT_SCENARIO):
    """Create test_user_001 and load a portfolio scenario."""
    print(f"\nCreating test user and portfolio (scenario: {scenario_id})...")

    user_data = UserCreate(
        clerk_user_id="test_user_001",
        display_name="Test User",
        years_until_retirement=25,
        target_retirement_income=Decimal("100000"),
    )

    existing = db_models.users.find_by_clerk_id("test_user_001")
    if existing:
        print("   Test user already exists")
    else:
        validated = user_data.model_dump()
        db_models.users.create_user(
            clerk_user_id=validated["clerk_user_id"],
            display_name=validated["display_name"],
            years_until_retirement=validated["years_until_retirement"],
            target_retirement_income=validated["target_retirement_income"],
        )
        print("   Created test user")

    user_accounts = db_models.accounts.find_by_user("test_user_001")
    if user_accounts:
        print(f"   User already has {len(user_accounts)} accounts (skipping portfolio load)")
        return

    result = apply_scenario(db_models, "test_user_001", scenario_id)
    print(f"   Loaded scenario: {result['scenario_name']}")
    for account in result["accounts"]:
        name = account.get("account_name", "Account")
        n_pos = len(account.get("positions") or [])
        print(f"   Created account: {name} ({n_pos} positions)")


def main():
    parser = argparse.ArgumentParser(description='Reset Alex database')
    parser.add_argument('--with-test-data', action='store_true',
                       help='Create test user with sample portfolio')
    scenario_ids = [s["id"] for s in list_scenarios()]
    parser.add_argument(
        '--scenario',
        default=DEFAULT_SCENARIO,
        choices=scenario_ids,
        help=f'Portfolio scenario when using --with-test-data (default: {DEFAULT_SCENARIO})',
    )
    parser.add_argument('--skip-drop', action='store_true',
                       help='Skip dropping tables (just reload data)')
    args = parser.parse_args()
    
    print("Database Reset Script")
    print("=" * 50)
    
    # Initialize database
    db = DataAPIClient()
    db_models = Database()
    
    if not args.skip_drop:
        # Drop all tables
        drop_all_tables(db)
        
        # Run migrations
        print("\nRunning migrations...")
        import subprocess
        result = subprocess.run(['uv', 'run', 'run_migrations.py'], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print("Migration failed!")
            print(result.stderr)
            print(result.stdout)
            sys.exit(1)
        else:
            print("Migrations completed")
    
    # Load seed data
    print("\nLoading seed data...")
    import subprocess
    result = subprocess.run(['uv', 'run', 'seed_data.py'], 
                          capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Seed data failed!")
        print(result.stderr)
        print(result.stdout)
        sys.exit(1)
    else:
        # Extract instrument count from output
        if '22/22 instruments loaded' in result.stdout:
            print("Loaded 22 instruments")
        else:
            print("Seed data loaded")
    
    # Create test data if requested
    if args.with_test_data:
        create_test_data(db_models, scenario_id=args.scenario)
    
    # Final verification
    print("\nFinal verification...")
    
    # Count records
    tables = ['users', 'instruments', 'accounts', 'positions', 'jobs']
    for table in tables:
        result = db.query(f"SELECT COUNT(*) as count FROM {table}")
        count = result[0]['count'] if result else 0
        print(f"   • {table}: {count} records")
    
    print("\n" + "=" * 50)
    print("Database reset complete!")
    
    if args.with_test_data:
        print("\nTest user created:")
        print("   • User ID: test_user_001")
        print("   • 3 accounts (401k, Roth IRA, Taxable)")
        print("   • 5 positions in 401k account")


if __name__ == "__main__":
    main()