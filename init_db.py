#!/usr/bin/env python3
"""
Database initialization script for Subscription Tracker
Ensures database is created with proper permissions and structure
"""

import os
import sys
import stat
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, '/app')

def check_database_permissions():
    """Check and fix database file permissions"""
    instance_dir = Path('/app/instance')
    db_file = instance_dir / 'subscriptions.db'
    
    print(f"Checking database permissions...")
    print(f"Instance directory: {instance_dir}")
    print(f"Database file: {db_file}")
    
    # Check if instance directory exists and is writable
    if not instance_dir.exists():
        print(f"ERROR: Instance directory {instance_dir} does not exist!")
        return False
    
    if not os.access(instance_dir, os.W_OK):
        print(f"ERROR: Instance directory {instance_dir} is not writable!")
        print(f"Current permissions: {oct(instance_dir.stat().st_mode)[-3:]}")
        print(f"Owner: {instance_dir.stat().st_uid}:{instance_dir.stat().st_gid}")
        print(f"Current user: {os.getuid()}:{os.getgid()}")
        return False
    
    # Check database file if it exists
    if db_file.exists():
        if not os.access(db_file, os.W_OK):
            print(f"ERROR: Database file {db_file} is not writable!")
            print(f"Current permissions: {oct(db_file.stat().st_mode)[-3:]}")
            print(f"Owner: {db_file.stat().st_uid}:{db_file.stat().st_gid}")
            return False
        else:
            print(f"Database file exists and is writable")
    else:
        print(f"Database file does not exist yet (will be created)")
    
    print("Database permissions check passed!")
    return True

def initialize_database():
    """Initialize the database with proper Flask app context"""
    try:
        from app import create_app, db
        
        # Create Flask app
        app = create_app()
        
        with app.app_context():
            print("Creating database tables...")
            
            # Create all tables
            db.create_all()
            
            # Verify tables were created
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"Created {len(tables)} tables: {', '.join(tables)}")
            
            # Test database write capability
            print("Testing database write capability...")
            result = db.engine.execute(db.text("SELECT 1 as test"))
            test_result = result.fetchone()
            print(f"Database connection test: {'PASSED' if test_result else 'FAILED'}")
            
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to initialize database: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main initialization function"""
    print("=" * 50)
    print("Database Initialization Script")
    print("=" * 50)
    
    # Check permissions first
    if not check_database_permissions():
        print("Permission check failed!")
        sys.exit(1)
    
    # Initialize database
    if not initialize_database():
        print("Database initialization failed!")
        sys.exit(1)
    
    print("=" * 50)
    print("Database initialization completed successfully!")
    print("=" * 50)

if __name__ == '__main__':
    main()