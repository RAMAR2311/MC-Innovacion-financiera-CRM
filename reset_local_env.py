import os
import shutil
from werkzeug.security import generate_password_hash
from app import app, db
from models import User

def reset_local_env():
    # 1. Limpiar Archivos Adjuntos (Uploads)
    uploads_dir = os.path.join(os.getcwd(), 'uploads')
    if os.path.exists(uploads_dir):
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
        # Si no existe, crearla para evitar errores futuros
        os.makedirs(uploads_dir, exist_ok=True)

    # 2. Reiniciar Base de Datos
    with app.app_context():
        # Borrar todo
        db.drop_all()
        
        # Crear todo nuevo
        db.create_all()

        # 3. Crear Admin por Defecto
        hashed_password = generate_password_hash('admin123', method='sha256')
        
        new_admin = User(
            nombre_completo="Admin Local",
            email="admin", # Usamos 'admin' como usuario según requerimiento (campo es email pero acepta string)
            telefono="0000000000",
            rol="Admin",
            password=hashed_password
        )
        
        db.session.add(new_admin)
        db.session.commit()
        
        print("✅ Entorno local limpio. Usuario admin/admin123 creado.")

if __name__ == "__main__":
    reset_local_env()
