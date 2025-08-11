#!/usr/bin/env python3
"""
Migration script to:
1. Add new unirate_api_key column to user_settings table
2. Copy data from fixer_api_key to unirate_api_key
3. Remove fixer_api_key column
4. Add exchange_rate table for daily caching
"""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    # Database path
    db_path = 'subscriptions.db'
    
    if not os.path.exists(db_path):
        print("Database file not found. Skipping migration.")
        return
    
    # Create backup
    backup_path = f'subscriptions_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    print(f"Creating backup: {backup_path}")
    
    with open(db_path, 'rb') as original:
        with open(backup_path, 'wb') as backup:
            backup.write(original.read())
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if unirate_api_key column already exists
        cursor.execute("PRAGMA table_info(user_settings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'unirate_api_key' not in columns:
            print("Adding unirate_api_key column...")
            cursor.execute("ALTER TABLE user_settings ADD COLUMN unirate_api_key VARCHAR(100)")
        
        # Copy data from fixer_api_key to unirate_api_key if fixer_api_key exists
        if 'fixer_api_key' in columns:
            print("Copying data from fixer_api_key to unirate_api_key...")
            cursor.execute("UPDATE user_settings SET unirate_api_key = fixer_api_key WHERE fixer_api_key IS NOT NULL")
            
            # Note: SQLite doesn't support DROP COLUMN directly for older versions
            # We'll leave the old column for now to avoid data loss
            print("Note: fixer_api_key column left in place for safety. It's no longer used by the application.")
        
        # Create exchange_rate table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exchange_rate (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                base_currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
                rates_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create unique index on date and base_currency
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_exchange_rate_date_base 
            ON exchange_rate (date, base_currency)
        """)
        
        conn.commit()
        print("Migration completed successfully!")
        print("✓ Added unirate_api_key column")
        print("✓ Copied existing API keys")
        print("✓ Created exchange_rate table for daily caching")
        print("✓ The application now uses UniRateAPI.com with daily caching")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
