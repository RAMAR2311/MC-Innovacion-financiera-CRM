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
                print("Column 'conclusion_analisis' added.")
            
            try:
                conn.execute(text("SELECT contract_number FROM client LIMIT 1"))
                print("Column 'contract_number' already exists.")
            except Exception:
                print("Adding 'contract_number' column...")
                conn.execute(text("ALTER TABLE client ADD COLUMN contract_number VARCHAR(50)"))
                print("Column 'contract_number' added.")

            try:
                conn.execute(text("SELECT last_status_update FROM client LIMIT 1"))
                print("Column 'last_status_update' already exists.")
            except Exception:
                print("Adding 'last_status_update' column...")
                conn.execute(text("ALTER TABLE client ADD COLUMN last_status_update DATETIME"))
                conn.execute(text("ALTER TABLE client ADD COLUMN last_status_update DATETIME"))
                print("Column 'last_status_update' added.")

            # Check for generic table creation (ClientNote, CaseMessage handled by db.create_all)
            # But we can verify if they exist in SQLite
            try:
                conn.execute(text("SELECT count(*) FROM client_note"))
                print("Table 'client_note' exists.")
            except:
                print("Table 'client_note' will be created by db.create_all().")

            try:
                conn.execute(text("SELECT count(*) FROM case_message"))
                print("Table 'case_message' exists.")
            except:
                print("Table 'case_message' will be created by db.create_all().")

if __name__ == '__main__':
    update_db()
