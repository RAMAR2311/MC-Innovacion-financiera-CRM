from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, Client
from services.user_service import UserService

from services.client_service import ClientService
from utils.decorators import role_required


admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@login_required
@role_required(['Admin'])
def admin_dashboard():

    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(page=page, per_page=20)
    return render_template('admin/dashboard.html', users=users)


@admin_bp.route('/admin/create_user', methods=['POST'])
@login_required
@role_required(['Admin'])
def create_user():

    
    try:
        UserService.create_user(request.form)
        flash('Usuario creado exitosamente', 'success')
    except ValueError as e:
        flash(str(e), 'warning')
    except Exception as e:
        flash(f'Error al crear usuario: {str(e)}', 'danger')

    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@role_required(['Admin'])
def delete_user(user_id):

    
    if user_id == current_user.id:
        flash('No puedes eliminar tu propio usuario.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))
    
    try:
        UserService.delete_user(user_id)
        flash('Usuario eliminado exitosamente.', 'success')
    except ValueError as e:
         flash(str(e), 'danger')
    except Exception as e:
        flash(f'Error al eliminar usuario: {str(e)}', 'danger')
        
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/client/<int:client_id>/generate_access', methods=['POST'])
@login_required
@role_required(['Admin'])
def generate_client_access(client_id):

    
    try:
        user = UserService.generate_client_access(client_id)
        flash(f'Usuario creado exitosamente. La contraseña temporal es: 123456', 'success')
    except ValueError as e:
        flash(str(e), 'warning')
    except Exception as e:
         flash(f'Error al generar acceso: {str(e)}', 'danger')
         
    return redirect(url_for('main.client_detail', client_id=client_id))

@admin_bp.route('/client/<int:client_id>/revoke_access', methods=['POST'])
@login_required
@role_required(['Admin'])
def revoke_client_access(client_id):

    
    try:
        UserService.disable_portal_access(client_id)
        flash('Acceso revocado correctamente.', 'success')
    except ValueError as e:
        flash(str(e), 'warning')
    except Exception as e:
        flash(f'Error al revocar acceso: {str(e)}', 'danger')
        
    return redirect(url_for('main.client_detail', client_id=client_id))


@admin_bp.route('/admin/delete_client/<int:client_id>', methods=['POST'])
@login_required
@role_required(['Admin'])
def delete_client(client_id):

    
    try:
        ClientService.delete_client(client_id)
        flash('Cliente y todos sus registros eliminados exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar cliente: {str(e)}', 'danger')
        
    return redirect(request.referrer or url_for('main.index'))
