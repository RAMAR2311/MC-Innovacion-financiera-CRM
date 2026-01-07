import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from app import app, db

# Connection parameters
DB_HOST = "localhost"
DB_PORT = "5432"
DB_USER = "postgres"
DB_PASS = "admin123"
DB_NAME = "crm_local"

def create_database():
    try:
        # Connect to default 'postgres' database
        con = psycopg2.connect(dbname='postgres', user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
        con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = con.cursor()
        
        # Check if database exists
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
        exists = cur.fetchone()
        
        if not exists:
            print(f"Creating database {DB_NAME}...")
            cur.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"Database {DB_NAME} created successfully.")
        else:
            print(f"Database {DB_NAME} already exists.")
            
        cur.close()
        con.close()
    except Exception as e:
        print(f"Error creating database: {e}")
        # If we can't connect to postgres db, maybe the user only has access to crm_local? 
        # But we'll assume standard setup.

def init_tables():
    print("Initializing tables...")
    try:
        with app.app_context():
            db.create_all()
            print("Tables created successfully.")
            
            # Verify if users exist
            from models import User
            if not User.query.first():
                print("No users found. You might want to create a default admin user.")
    except Exception as e:
        print(f"Error initializing tables: {e}")

if __name__ == "__main__":
    create_database()
    init_tables()
