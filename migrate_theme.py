#!/usr/bin/env python3
"""
Migration script to add theme columns to UserSettings table
"""

import sys
import os

# Add the app directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import UserSettings

def migrate_database():
    """Add theme columns to existing UserSettings table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [column['name'] for column in inspector.get_columns('user_settings')]
            
            # Add theme_mode column if it doesn't exist
            if 'theme_mode' not in columns:
                db.engine.execute("ALTER TABLE user_settings ADD COLUMN theme_mode VARCHAR(10) DEFAULT 'light'")
                print("Added theme_mode column")
            else:
                print("theme_mode column already exists")
            
            # Add accent_color column if it doesn't exist  
            if 'accent_color' not in columns:
                db.engine.execute("ALTER TABLE user_settings ADD COLUMN accent_color VARCHAR(10) DEFAULT 'purple'")
                print("Added accent_color column")
            else:
                print("accent_color column already exists")
                
            print("Migration completed successfully!")
            
        except Exception as e:
            print(f"Migration failed: {e}")
            return False
    
    return True

if __name__ == "__main__":
    migrate_database()
