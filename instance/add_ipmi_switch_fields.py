"""
Add IPMI switch tracking columns to existing servers table
"""

import sqlite3

print("=" * 50)
print("Adding IPMI Switch columns to servers table")
print("=" * 50)

conn = sqlite3.connect('dcms.db')
cursor = conn.cursor()

try:
    # Add ipmi_switch_id column
    cursor.execute("ALTER TABLE servers ADD COLUMN ipmi_switch_id INTEGER")
    print("✓ Added ipmi_switch_id column")
    
    # Add ipmi_switch_port_id column
    cursor.execute("ALTER TABLE servers ADD COLUMN ipmi_switch_port_id INTEGER")
    print("✓ Added ipmi_switch_port_id column")
    
    # Commit the changes
    conn.commit()
    
    print("\n✅ SUCCESS! Both columns added.")
    print("\n🎉 You can now restart your Flask application!")
    
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("⚠ Columns already exist")
    else:
        print(f"❌ Error: {e}")
        conn.rollback()
        
finally:
    conn.close()

print("=" * 50)