from app import app, db
from models import User, Client, FinancialObligation, Interaction, Sale, Installment, Document, PaymentDiagnosis, PaymentContract, ContractInstallment

def reset_database():
    with app.app_context():
        print("--- INICIANDO PROTOCOLO DE LIMPIEZA DE BASE DE DATOS ---")
        
        # 1. Delete Child Tables (Reverse dependency order to avoid FK issues)
        print("1. Eliminando Cuotas de Contratos (ContractInstallment)...")
        deleted = db.session.query(ContractInstallment).delete()
        print(f"   -> {deleted} registros eliminados.")
        
        print("2. Eliminando Contratos de Pago (PaymentContract)...")
        deleted = db.session.query(PaymentContract).delete()
        print(f"   -> {deleted} registros eliminados.")

        print("3. Eliminando Diagnósticos de Pago (PaymentDiagnosis)...")
        deleted = db.session.query(PaymentDiagnosis).delete()
        print(f"   -> {deleted} registros eliminados.")
        
        print("4. Eliminando Documentos (Document)...")
        deleted = db.session.query(Document).delete()
        print(f"   -> {deleted} registros eliminados.")
        
        print("5. Eliminando Cuotas de Ventas (Installment - Legacy)...")
        deleted = db.session.query(Installment).delete()
        print(f"   -> {deleted} registros eliminados.")
        
        print("6. Eliminando Ventas (Sale)...")
        deleted = db.session.query(Sale).delete()
        print(f"   -> {deleted} registros eliminados.")

        print("7. Eliminando Obligaciones Financieras (FinancialObligation)...")
        deleted = db.session.query(FinancialObligation).delete()
        print(f"   -> {deleted} registros eliminados.")
        
        print("8. Eliminando Interacciones (Interaction)...")
        deleted = db.session.query(Interaction).delete()
        print(f"   -> {deleted} registros eliminados.")

        # 2. Delete Clients (Parents of above, Children of Users)
        print("9. Eliminando Clientes (Client)...")
        deleted = db.session.query(Client).delete()
        print(f"   -> {deleted} registros eliminados.")

        # 3. Delete Users EXCEPT 'admin@mc.com'
        print("10. Eliminando Usuarios (User) excepto 'admin@mc.com'...")
        admin_email = 'admin@mc.com'
        
        # Verify Admin exists before deleting others, to start safe
        admin_user = User.query.filter_by(email=admin_email).first()
        if not admin_user:
            print("   [ALERTA] No se encontró al usuario 'admin@mc.com'. Se creará uno por seguridad.")
            # Create admin if missing (just in case)
            admin_user = User(nombre_completo='Admin', email='admin@mc.com', rol='Admin', password='admin')
            db.session.add(admin_user)
            db.session.commit()
            print("   -> Usuario Admin creado/restaurado.")

        # Delete everyone else
        deleted = db.session.query(User).filter(User.email != admin_email).delete()
        print(f"   -> {deleted} usuarios eliminados.")

        # 4. Commit Final
        try:
            db.session.commit()
            print("\n--- LIMPIEZA COMPLETADA CON ÉXITO ---")
            print("El sistema está limpio list para producción.")
            print("Único usuario activo: admin@mc.com")
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] Ocurrió un error al hacer commit: {e}")

if __name__ == '__main__':
    reset_database()
