import os
import shutil
import getpass
from werkzeug.security import generate_password_hash
from app import app, db
from models import User

def reset_prod_keep_admin():
    print("!!! ADVERTENCIA DE SEGURIDAD !!!")
    print("Este script eliminará TODA la base de datos y los archivos adjuntos.")
    print("Esta acción es IRREVERSIBLE.")
    confirm = input("¿Estás seguro de borrar TODOS los datos del CRM? (y/n): ")
    
    if confirm.lower() != 'y':
        print("Operación cancelada.")
        return

    # 1. Limpiar Archivos Adjuntos (Uploads)
    uploads_dir = os.path.join(os.getcwd(), 'uploads')
    if os.path.exists(uploads_dir):
        print(f"Limpiando carpeta de subidas: {uploads_dir}")
        for filename in os.listdir(uploads_dir):
            if filename == '.gitignore':
                continue
            
            file_path = os.path.join(uploads_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Fallo al borrar {file_path}. Razón: {e}')
    else:
        print("La carpeta 'uploads' no existe, se omitirá la limpieza.")

    # 2. Reiniciar Base de Datos
    with app.app_context():
        print("Eliminando base de datos actual...")
        db.drop_all()
        print("Base de datos eliminada.")
        
        print("Creando nuevas tablas...")
        db.create_all()
        print("Tablas creadas exitosamente.")

        # 3. Restaurar Admin
        print("\n--- Configuración del Nuevo Administrador ---")
        username = "admin" # Fijo según requerimiento
        # Campos obligatorios User: nombre_completo, telefono, email, rol, password
        
        password = getpass.getpass("Ingrese la contraseña para el Admin (Enter para 'admin123'): ")
        if not password:
            password = 'admin123'
        
        hashed_password = generate_password_hash(password, method='sha256')
        
        new_admin = User(
            nombre_completo="Administrador del Sistema",
            email="admin@zenic.com", # Email default, puede cambiarse luego
            telefono="0000000000",
            rol="Admin",
            password=hashed_password
        )
        
        db.session.add(new_admin)
        db.session.commit()
        
        print(f"\n[ÉXITO] Sistema reiniciado.")
        print(f"Usuario Admin creado: {new_admin.email} / (Contraseña proporcionada)")

if __name__ == "__main__":
    reset_prod_keep_admin()
