"""
Migration script to add VLAN field to network_devices table
Run this once to update your existing database
"""

import sqlite3
import sys

def migrate():
    try:
        # Connect to the database
        conn = sqlite3.connect('dcms.db')
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(network_devices)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'vlan_id' in column_names:
            print("✓ vlan_id column already exists in network_devices table")
            return
        
        # Add the vlan_id column
        cursor.execute("""
            ALTER TABLE network_devices 
            ADD COLUMN vlan_id INTEGER 
            REFERENCES vlans(id)
        """)
        
        conn.commit()
        print("✅ Successfully added vlan_id column to network_devices table")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
    print("\nMigration complete! You can now run app.py")