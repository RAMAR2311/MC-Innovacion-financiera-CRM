import sqlite3
import os

DB_PATH = os.path.join('instance', 'crm.db')

def update_schema():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(client)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'login_user_id' not in columns:
            print("Adding login_user_id column to client table...")
            cursor.execute("ALTER TABLE client ADD COLUMN login_user_id INTEGER REFERENCES user(id)")
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column login_user_id already exists.")

    except Exception as e:
        print(f"Error updating schema: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_schema()
