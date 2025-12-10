from app import app, db
from models import Client, FinancialObligation, PaymentDiagnosis, PaymentContract, ContractInstallment, Document

def reset_data():
    with app.app_context():
        print("Iniciando limpieza de datos de prueba...")
        
        # 1. Cuotas (Dependen de PaymentContract)
        deleted_installments = db.session.query(ContractInstallment).delete()
        print(f"Eliminadas {deleted_installments} cuotas.")
        
        # 2. Contratos y Diagnósticos (Dependen de Client)
        deleted_contracts = db.session.query(PaymentContract).delete()
        print(f"Eliminados {deleted_contracts} contratos.")
        
        deleted_diagnosis = db.session.query(PaymentDiagnosis).delete()
        print(f"Eliminados {deleted_diagnosis} diagnósticos.")
        
        # 3. Obligaciones Financieras (Dependen de Client)
        deleted_obligations = db.session.query(FinancialObligation).delete()
        print(f"Eliminadas {deleted_obligations} obligaciones financieras.")
        
        # 4. Documentos (Dependen de Client)
        deleted_documents = db.session.query(Document).delete()
        print(f"Eliminados {deleted_documents} documentos.")
        
        # 5. Clientes (Raíz)
        deleted_clients = db.session.query(Client).delete()
        print(f"Eliminados {deleted_clients} clientes.")
        
        db.session.commit()
        print("-" * 30)
        print("Base de datos limpia. Lista para clientes reales.")
        print("(Los usuarios Admin/Abogado/Analista se han conservado).")

if __name__ == "__main__":
    reset_data()
