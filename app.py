from flask import Flask, render_template, flash, redirect, url_for
from models import db, User
from flask_login import LoginManager, current_user
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from config import Config
from flask_wtf.csrf import CSRFProtect, CSRFError

from flask_migrate import Migrate

app = Flask(__name__)
app.config.from_object(Config)

csrf = CSRFProtect(app)

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash('Sesión expirada o token inválido. Por favor, intenta nuevamente.', 'danger')
    return redirect(url_for('login'))

db.init_app(app)
migrate = Migrate(app, db) # Initialize Flask-Migrate

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.analyst import analyst_bp
from routes.lawyer import lawyer_bp
from routes.aliados import aliados_bp
from routes.chat import chat_bp
from routes.main import main_bp
from routes.financial import financial_bp
from routes.radicador import radicador_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(analyst_bp)
app.register_blueprint(lawyer_bp)
app.register_blueprint(aliados_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(financial_bp)
app.register_blueprint(radicador_bp)
app.register_blueprint(main_bp)


from models import CaseMessage, Client

@app.context_processor
def inject_notifications():
    if not current_user.is_authenticated:
        return dict(unread_messages_count=0, notifications_list={})
    
    total_count = 0
    notifications_list = {}
    
    if current_user.rol == 'Cliente':
        # Buscamos el cliente asociado a este usuario de login
        user_client = Client.query.filter_by(login_user_id=current_user.id).first()
        if user_client:
            unread_msgs = CaseMessage.query.filter(
                CaseMessage.client_id == user_client.id,
                CaseMessage.sender_id != current_user.id,
                CaseMessage.is_read_by_recipient == False
            ).all()
            total_count = len(unread_msgs)
            if total_count > 0:
                notifications_list[user_client.id] = {
                    'name': 'Mi Abogado',
                    'count': total_count,
                    'id': user_client.id
                }
            
    elif current_user.rol in ['Abogado', 'Admin']:
        # Para abogados, solo mensajes de sus clientes asignados.
        # Para Admin, podríamos mostrar todos o seguir la misma lógica.
        query = CaseMessage.query.filter(
            CaseMessage.sender_id != current_user.id,
            CaseMessage.is_read_by_recipient == False
        )
        
        if current_user.rol == 'Abogado':
            query = query.join(Client).filter(Client.abogado_id == current_user.id)
        
        unread_msgs = query.all()
        total_count = len(unread_msgs)
        
        for msg in unread_msgs:
            c_id = msg.client_id
            if c_id not in notifications_list:
                notifications_list[c_id] = {
                    'name': msg.client.nombre,
                    'count': 0,
                    'id': c_id
                }
            notifications_list[c_id]['count'] += 1
            
    return dict(unread_messages_count=total_count, notifications_list=notifications_list)

if __name__ == '__main__':
    with app.app_context():
        # db.create_all() # Removed in favor of Flask-Migrate

        # Create default admin if not exists
        if not User.query.filter_by(email='admin@mc.com').first():
            from werkzeug.security import generate_password_hash
            hashed_pw = generate_password_hash('admin')
            admin = User(nombre_completo='Admin', email='admin@mc.com', rol='Admin', password=hashed_pw) 
            db.session.add(admin)
            db.session.commit()
            print("Admin user created.")
    
    app.run(debug=True)
