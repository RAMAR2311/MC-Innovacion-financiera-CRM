
from flask import Flask, render_template
from models import db, User
from flask_login import LoginManager
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui' # Cambiar en produccion
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

db.init_app(app)
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
from routes.main import main_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(analyst_bp)
app.register_blueprint(lawyer_bp)
app.register_blueprint(aliados_bp)
app.register_blueprint(main_bp)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create default admin if not exists
        if not User.query.filter_by(email='admin@mc.com').first():
            admin = User(nombre_completo='Admin', email='admin@mc.com', rol='Admin', password='admin') 
            db.session.add(admin)
            db.session.commit()
            print("Admin user created.")
    
    app.run(debug=True)
