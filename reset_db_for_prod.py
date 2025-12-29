from app import app, db
from models import (
    User, Client, FinancialObligation, Interaction, Sale, 
    Installment, Document, PaymentDiagnosis, PaymentContract, 
    ContractInstallment
)
import sys

def reset_db():
    print("Starting database cleanup...")
    with app.app_context():
        # Verify Admin exists first
        admin_email = 'admin@mc.com'
        admin = User.query.filter_by(email=admin_email).first()
        
        if not admin:
            print(f"CRITICAL WARNING: Admin user '{admin_email}' not found. Aborting to prevent total lockout.")
            sys.exit(1)
        
        print(f"Admin user found: {admin.nombre_completo} (ID: {admin.id}). Preserving...")

        try:
            # Delete dependent tables first (children)
            print("Deleting ContractInstallments...")
            db.session.query(ContractInstallment).delete()
            
            print("Deleting Installments (Sales)...")
            db.session.query(Installment).delete()
            
            print("Deleting PaymentContracts...")
            db.session.query(PaymentContract).delete()
            
            print("Deleting PaymentDiagnoses...")
            db.session.query(PaymentDiagnosis).delete()
            
            print("Deleting Documents...")
            db.session.query(Document).delete()
            
            print("Deleting Sales...")
            db.session.query(Sale).delete()
            
            print("Deleting interactions...")
            db.session.query(Interaction).delete()
            
            print("Deleting FinancialObligations...")
            db.session.query(FinancialObligation).delete()
            
            # Delete Clients (parents of above, child of User)
            print("Deleting Clients...")
            db.session.query(Client).delete()
            
            # Delete Users except Admin
            print("Deleting Users (except Admin)...")
            deleted_users = db.session.query(User).filter(User.email != admin_email).delete()
            print(f"Deleted {deleted_users} users.")
            
            # Commit changes
            db.session.commit()
            print("Database cleanup completed successfully.")
            print("System is ready for production. ONLY 'admin@mc.com' remains.")
            
        except Exception as e:
            db.session.rollback()
            print(f"An error occurred: {e}")
            print("Rolled back changes.")

if __name__ == "__main__":
    reset_db()
