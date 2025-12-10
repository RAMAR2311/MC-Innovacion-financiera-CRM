from app import app, db
from sqlalchemy import text

def update_db():
    with app.app_context():
        # 1. Create new table
        db.create_all()
        print("Created new tables (if any).")

        # 2. Add column to existing table (SQLite specific)
        # Check if column exists first to avoid error
        with db.engine.connect() as conn:
            try:
                # Try to select the column to see if it exists
                conn.execute(text("SELECT conclusion_analisis FROM client LIMIT 1"))
                print("Column 'conclusion_analisis' already exists.")
            except Exception:
                # If error, column likely doesn't exist, so add it
                print("Adding 'conclusion_analisis' column...")
                conn.execute(text("ALTER TABLE client ADD COLUMN conclusion_analisis TEXT"))
                print("Column added.")

if __name__ == '__main__':
    update_db()
