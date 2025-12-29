from app import app, db
from sqlalchemy import text

def add_column():
    with app.app_context():
        try:
            # Check if column exists
            with db.engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(document)"))
                columns = [row[1] for row in result.fetchall()]
                
                if 'visible_para_cliente' not in columns:
                    print("Adding visible_para_cliente column to Document table...")
                    conn.execute(text("ALTER TABLE document ADD COLUMN visible_para_cliente BOOLEAN DEFAULT 0"))
                    conn.commit()
                    print("Column added successfully.")
                else:
                    print("Column visible_para_cliente already exists.")
        except Exception as e:
            print(f"Error updating database: {e}")

if __name__ == "__main__":
    add_column()
