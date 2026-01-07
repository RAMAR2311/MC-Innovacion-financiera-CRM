from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user:
            is_valid = False
            # 1. Try secure hash check
            if user.password and check_password_hash(user.password, password):
                is_valid = True
            # 2. Fallback for old plaintext passwords (Migration Logic)
            elif user.password == password:
                is_valid = True
                # Automatically upgrade to hash for next time
                user.password = generate_password_hash(password)
                db.session.commit()

            if is_valid:
                if not user.is_active:
                    flash('Tu cuenta ha sido desactivada. Por favor contacta al administrador.', 'warning')
                    return redirect(url_for('auth.login'))
                login_user(user)

                if user.rol == 'Cliente':
                    return redirect(url_for('main.client_portal'))
                elif user.rol == 'Admin':
                    return redirect(url_for('admin.admin_dashboard'))
                elif user.rol == 'Analista':
                    return redirect(url_for('analyst.analyst_dashboard'))
                elif user.rol == 'Aliado':
                    return redirect(url_for('aliados.aliados_dashboard'))
                elif user.rol == 'Abogado':
                    return redirect(url_for('lawyer.lawyer_dashboard'))
                return redirect(url_for('main.index'))
                
        flash('Credenciales inválidas', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not current_password or not new_password or not confirm_password:
            flash('Todos los campos son obligatorios.', 'warning')
        elif not check_password_hash(current_user.password, current_password):
            flash('La contraseña actual es incorrecta.', 'danger')
        elif new_password != confirm_password:
            flash('Las nuevas contraseñas no coinciden.', 'warning')
        else:
            current_user.password = generate_password_hash(new_password)
            db.session.commit()
            flash('Contraseña actualizada exitosamente.', 'success')
            
            # Redirect based on role
            if current_user.rol == 'Cliente':
                return redirect(url_for('main.client_portal'))
            elif current_user.rol == 'Admin':
                return redirect(url_for('admin.admin_dashboard'))
            elif current_user.rol == 'Analista':
                return redirect(url_for('analyst.analyst_dashboard'))
            elif current_user.rol == 'Abogado':
                return redirect(url_for('lawyer.lawyer_dashboard'))
            return redirect(url_for('main.index'))

        # On error, redirect back to the previous page if possible, or default to index
        return redirect(request.referrer or url_for('main.index'))
    
    # If GET, just redirect to index as this is intended to be used via modal
    return redirect(url_for('main.index'))
