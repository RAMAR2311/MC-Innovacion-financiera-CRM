import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_tables():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("DATABASE_URL not set.")
        return

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # PostgreSQL query to list tables in the public schema
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public';
        """)
        
        tables = cursor.fetchall()
        print("Tables found in PostgreSQL:", [t[0] for t in tables])
        
        conn.close()
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")

if __name__ == '__main__':
    check_tables()
