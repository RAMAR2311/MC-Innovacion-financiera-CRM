from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, Client
from sqlalchemy.exc import IntegrityError

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@login_required
def admin_dashboard():
    if current_user.rol != 'Admin':
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('main.index'))
    users = User.query.all()
    return render_template('admin/dashboard.html', users=users)

@admin_bp.route('/admin/create_user', methods=['POST'])
@login_required
def create_user():
    if current_user.rol != 'Admin':
        return redirect(url_for('main.index'))
    
    nombre = request.form.get('nombre')
    email = request.form.get('email')
    password = request.form.get('password')
    rol = request.form.get('rol')
    telefono = request.form.get('telefono')

    if User.query.filter_by(email=email).first():
        flash('El email ya existe', 'warning')
    else:
        new_user = User(nombre_completo=nombre, email=email, password=password, rol=rol, telefono=telefono)
        db.session.add(new_user)
        db.session.commit()
        flash('Usuario creado exitosamente', 'success')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.rol != 'Admin':
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('main.index'))
    
    if user_id == current_user.id:
        flash('No puedes eliminar tu propio usuario.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash('Usuario eliminado exitosamente.', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('No se puede eliminar este usuario porque tiene clientes o registros asignados. Intenta reasignar sus casos primero.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar usuario: {str(e)}', 'danger')
        
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/client/<int:client_id>/generate_access', methods=['POST'])
@login_required
def generate_client_access(client_id):
    if current_user.rol != 'Admin':
        flash('No autorizado', 'danger')
        return redirect(url_for('main.index'))
    
    client = Client.query.get_or_404(client_id)
    email = client.email
    if not email:
        flash('El cliente no tiene un email registrado.', 'danger')
        return redirect(url_for('main.client_detail', client_id=client_id))

    # Auto-generate or set default password
    password = "Cliente2024*" 
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash(f'El usuario con email {email} ya existe.', 'warning')
        # Optional: Link if not linked? For now just warn.
        if not client.login_user_id:
             client.login_user_id = existing_user.id
             db.session.commit()
             flash('Se ha vinculado el usuario existente al cliente.', 'info')
        return redirect(url_for('main.client_detail', client_id=client_id))
    
    # Create new User
    # Note: In production use hashed passwords!
    new_user = User(
        nombre_completo=client.nombre,
        email=email,
        password=password, 
        rol='Cliente',
        telefono=client.telefono
    )
    db.session.add(new_user)
    db.session.flush() # to get ID
    
    # Link to Client
    client.login_user_id = new_user.id
    db.session.commit()
    
    flash(f'Usuario creado exitosamente. La contraseña temporal es: {password}', 'success')
    return redirect(url_for('main.client_detail', client_id=client_id))

@admin_bp.route('/admin/delete_client/<int:client_id>', methods=['POST'])
@login_required
def delete_client(client_id):
    if current_user.rol != 'Admin':
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('main.index'))
    
    client = Client.query.get_or_404(client_id)
    
    try:
        db.session.delete(client)
        db.session.commit()
        flash('Cliente y todos sus registros eliminados exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar cliente: {str(e)}', 'danger')
        
    return redirect(request.referrer or url_for('main.index'))
