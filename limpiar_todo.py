from app import app, db
from models import (
    User, Client, FinancialObligation, Interaction, Sale, Installment,
    Document, PaymentDiagnosis, PaymentContract, ContractInstallment,
    ChatMessage, CaseMessage, ClientNote, AllyPayment, AdministrativeExpense
)
import sys

def main():
    print("===================================================")
    print("   ⚠️  ATENCIÓN: SCRIPT DE MANTENIMIENTO CRÍTICO ⚠️")
    print("===================================================")
    print("ESTA ACCIÓN ELIMINARÁ TODOS LOS DATOS (CLIENTES, PAGOS, CHATS, ETC.)")
    print("SOLO SE CONSERVARÁ EL SUPER ADMIN (admin@mc.com)")
    print("===================================================")
    
    confirmacion = input("¿ESTÁS SEGURO? (s/n): ").strip().lower()
    
    if confirmacion != 's':
        print("Operación cancelada por el usuario.")
        return

    with app.app_context():
        try:
            print("\nIniciando proceso de limpieza...")
            
            # 1. Seguridad del Admin
            print("1. Buscando al Super Admin 'admin@mc.com'...")
            admin = User.query.filter_by(email='admin@mc.com').first()
            
            if not admin:
                print("❌ ERROR CRÍTICO: No se encontró el usuario 'admin@mc.com'.")
                print("ABORTANDO OPERACIÓN para evitar bloqueo total del sistema.")
                return
            
            admin_id = admin.id
            print(f"✅ Admin encontrado (ID: {admin_id}). Se protegerá este usuario.")

            # 2. Borrado en Cascada Manual
            print("\n--- Borrando Tablas Hijas (nivel bajo) ---")
            
            print("- Eliminando ContractInstallment...")
            cnt_ci = ContractInstallment.query.delete()
            print(f"  -> {cnt_ci} registros eliminados.")

            print("- Eliminando Installment...")
            cnt_i = Installment.query.delete()
            print(f"  -> {cnt_i} registros eliminados.")

            print("- Eliminando ChatMessage...")
            cnt_chat = ChatMessage.query.delete()
            print(f"  -> {cnt_chat} registros eliminados.")

            print("- Eliminando CaseMessage...")
            cnt_case = CaseMessage.query.delete()
            print(f"  -> {cnt_case} registros eliminados.")

            print("- Eliminando ClientNote...")
            cnt_note = ClientNote.query.delete()
            print(f"  -> {cnt_note} registros eliminados.")

            print("- Eliminando AllyPayment...")
            cnt_ally = AllyPayment.query.delete()
            print(f"  -> {cnt_ally} registros eliminados.")

            print("\n--- Borrando Tablas Intermedias ---")
            
            print("- Eliminando PaymentContract...")
            cnt_pc = PaymentContract.query.delete()
            print(f"  -> {cnt_pc} registros eliminados.")

            print("- Eliminando PaymentDiagnosis...")
            cnt_pd = PaymentDiagnosis.query.delete()
            print(f"  -> {cnt_pd} registros eliminados.")

            print("- Eliminando FinancialObligation...")
            cnt_fo = FinancialObligation.query.delete()
            print(f"  -> {cnt_fo} registros eliminados.")

            print("- Eliminando Sale...")
            cnt_sale = Sale.query.delete()
            print(f"  -> {cnt_sale} registros eliminados.")

            print("- Eliminando Document...")
            cnt_doc = Document.query.delete()
            print(f"  -> {cnt_doc} registros eliminados.")

            print("- Eliminando Interaction...")
            cnt_int = Interaction.query.delete()
            print(f"  -> {cnt_int} registros eliminados.")

            print("- Eliminando AdministrativeExpense...")
            cnt_exp = AdministrativeExpense.query.delete()
            print(f"  -> {cnt_exp} registros eliminados.")

            print("\n--- Borrando Tablas Padres ---")
            
            print("- Eliminando Client...")
            cnt_cli = Client.query.delete()
            print(f"  -> {cnt_cli} registros eliminados.")

            # 3. Usuarios (Excluyendo Admin)
            print("\n--- Borrando Usuarios (Excepto Admin) ---")
            cnt_users = User.query.filter(User.id != admin_id).delete(synchronize_session=False)
            print(f"  -> {cnt_users} usuarios eliminados. (Admin ID {admin_id} conservado)")

            # Confirmación final
            db.session.commit()
            print("\n===================================================")
            print("✅ LIMPIEZA COMPLETADA EXITOSAMENTE")
            print("===================================================")
            print("La base de datos está lista para producción.")

        except Exception as e:
            db.session.rollback()
            print("\n❌ ERROR CRÍTICO DURANTE LA EJECUCIÓN:")
            print(str(e))
            print("---------------------------------------------------")
            print("SE HA REALIZADO UN ROLLBACK. NO SE HAN BORRADO DATOS.")
            print("===================================================")

if __name__ == "__main__":
    main()
