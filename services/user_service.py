from models import db, User, Client
from sqlalchemy.exc import IntegrityError
from typing import Dict, Any, Optional
from werkzeug.security import generate_password_hash

class UserService:
    @staticmethod
    def create_user(data: Dict[str, Any]) -> User:
        """
        Creates a new user.
        """
        nombre = data.get('nombre')
        email = data.get('email')
        password = data.get('password')
        rol = data.get('rol')
        telefono = data.get('telefono')

        if User.query.filter_by(email=email).first():
            raise ValueError('El email ya existe')

        new_user = User(
            nombre_completo=nombre, 
            email=email, 
            password=generate_password_hash(password) if password else None, 
            rol=rol, 
            telefono=telefono
        )
        db.session.add(new_user)
        db.session.commit()
        return new_user

    @staticmethod
    def delete_user(user_id: int) -> None:
        """
        Deletes a user by ID.
        """
        user = User.query.get_or_404(user_id)
        
        try:
            db.session.delete(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError('No se puede eliminar este usuario porque tiene clientes o registros asignados. Intenta reasignar sus casos primero.')
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def generate_client_access(client_id: int) -> Optional[User]:
        """
        Generates or links a user account for a client.
        """
        client = Client.query.get_or_404(client_id)
        email = client.email
        
        if not email:
            raise ValueError('El cliente no tiene un email registrado.')

        # Auto-generate or set default password
        # Security: Default password 123456 hashed properly
        plain_password = "123456"
        password_hash = generate_password_hash(plain_password) 
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            # Check if already linked
            if not client.login_user_id:
                 client.login_user_id = existing_user.id
                 # Reactivate if it was disabled
                 existing_user.is_active = True
                 db.session.commit()
                 raise ValueError(f'El usuario con email {email} ya existe. Se ha vinculado al cliente y se ha habilitado el acceso.')
            else:
                 # Reactivate if it was disabled
                 if not existing_user.is_active:
                     existing_user.is_active = True
                     db.session.commit()
                     return existing_user
                 raise ValueError(f'El usuario con email {email} ya existe y ya está habilitado.')

        
        # Create new User
        new_user = User(
            nombre_completo=client.nombre,
            email=email,
            password=password_hash, 
            rol='Cliente',
            telefono=client.telefono
        )
        db.session.add(new_user)
        db.session.flush() # to get ID
        
        # Link to Client
        client.login_user_id = new_user.id
        db.session.commit()
        
        return new_user

    @staticmethod
    def disable_portal_access(client_id: int) -> None:
        """
        Disables portal access for a client by setting the user as inactive.
        """
        client = Client.query.get_or_404(client_id)
        if not client.login_user_id:
            raise ValueError('El cliente no tiene un usuario asociado.')
        
        user = User.query.get(client.login_user_id)
        if user:
            user.is_active = False
            db.session.commit()

