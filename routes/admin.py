from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, Client, PaymentDiagnosis, ContractInstallment, PaymentContract
from services.user_service import UserService

from services.client_service import ClientService
from services.document_service import DocumentService
from services.financial_service import FinancialService
from utils.decorators import role_required


admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@login_required
@role_required(['Admin'])
def admin_dashboard():

    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(page=page, per_page=20)
    all_analysts = User.query.filter(User.rol.in_(['Analista', 'Aliado', 'Admin'])).all()
    return render_template('admin/dashboard.html', users=users, all_analysts=all_analysts)


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

@admin_bp.route('/admin/reassign_analyst', methods=['POST'])
@login_required
@role_required(['Admin'])
def reassign_analyst():
    old_analyst_id = request.form.get('old_analyst_id')
    new_analyst_id = request.form.get('new_analyst_id')

    if not old_analyst_id or not new_analyst_id:
        flash('Debes seleccionar ambos analistas.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    if old_analyst_id == new_analyst_id:
        flash('El analista de origen y destino deben ser diferentes.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    try:
        # Bulk update for efficiency
        affected_rows = Client.query.filter_by(analista_id=old_analyst_id).update({Client.analista_id: new_analyst_id})
        db.session.commit()
        
        if affected_rows > 0:
            flash(f'Se reasignaron exitosamente {affected_rows} clientes.', 'success')
        else:
            flash('El analista de origen no tenía clientes asignados.', 'info')

    except Exception as e:
        db.session.rollback()
        flash(f'Error durante la reasignación: {str(e)}', 'danger')

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

@admin_bp.route('/admin/delete_document/<int:doc_id>', methods=['POST'])
@login_required
@role_required(['Admin'])
def delete_document(doc_id):
    try:
        DocumentService.delete_document(doc_id)
        flash('Documento eliminado exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar documento: {str(e)}', 'danger')
        
    return redirect(request.referrer or url_for('main.index'))

@admin_bp.route('/admin/delete_obligation/<int:obligation_id>', methods=['POST'])
@login_required
@role_required(['Admin'])
def delete_obligation(obligation_id):
    try:
        FinancialService.delete_obligation(obligation_id)
        flash('Obligación financiera eliminada exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar obligación: {str(e)}', 'danger')
        
    return redirect(request.referrer or url_for('main.index'))

@admin_bp.route('/reports')
@login_required
@role_required(['Admin'])
def reports():
    report_data = {}

    # 1. Aggregating Diagnosis Payments
    # Looking for PaymentDiagnosis records
    diagnoses = PaymentDiagnosis.query.all()
    for diag in diagnoses:
        if not diag.valor or diag.valor <= 0:
            continue
            
        method = diag.metodo_pago.strip().capitalize() if diag.metodo_pago else 'Desconocido'
        
        if method not in report_data:
            report_data[method] = {'total': 0, 'transactions': []}
            
        report_data[method]['total'] += float(diag.valor)
        report_data[method]['transactions'].append({
            'date': diag.fecha_pago,
            'client': diag.client.nombre if diag.client else 'Cliente Eliminado',
            'client_id': diag.client.id if diag.client else None,
            'type': 'Diagnóstico Inicial',
            'amount': float(diag.valor)
        })

    # 2. Aggregating Contract Installments
    # Filter only paid installments
    installments = ContractInstallment.query.filter(
        ContractInstallment.estado.in_(['Pagada', 'Pagado', 'Aprobado'])
    ).all()
    
    for inst in installments:
        if not inst.valor or inst.valor <= 0:
            continue
            
        method = inst.metodo_pago.strip().capitalize() if inst.metodo_pago else 'Desconocido'
        
        if method not in report_data:
            report_data[method] = {'total': 0, 'transactions': []}
            
        report_data[method]['total'] += float(inst.valor)
        
        # Try to get client name back via relationship chain: Installment -> Contract -> Client
        client_name = 'Desconocido'
        client_id = None
        if inst.payment_contract and inst.payment_contract.client:
            client_name = inst.payment_contract.client.nombre
            client_id = inst.payment_contract.client.id
            
        report_data[method]['transactions'].append({
            'date': inst.fecha_vencimiento, # Or create a paid_date field if it existed, falling back to due date or we assume paid near then. Ideally Installment should have payment date.
            # Checking valid fields: Installment has 'fecha_vencimiento'. Only 'fecha_pago' is on Sale > Installment (old model?). 
            # ContractInstallment (new model) has 'fecha_vencimiento'. It does NOT seem to have 'fecha_pago' based on previous context.
            # I will use 'fecha_vencimiento' as proxy for date in report or TODAY/None if not sure. 
            # Actually, looking at models.py Line 133: fecha_vencimiento. 
            # It seems ContractInstallment tracks schedule. 
            # When paid, ideally we should track when. But for now I'll use vencimiento as the reference date.
            # When paid, ideally we should track when. But for now I'll use vencimiento as the reference date.
            'client': client_name,
            'client_id': client_id,
            'type': f'Cuota {inst.numero_cuota}',
            'amount': float(inst.valor)
        })
        
    return render_template('admin/reports.html', report_data=report_data)

@admin_bp.route('/admin/import_clients', methods=['POST'])
@login_required
@role_required(['Admin', 'Analista', 'Aliado'])
def import_clients():
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo', 'danger')
        return _redirect_after_import()
        
    file = request.files['file']
    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'danger')
        return _redirect_after_import()
        
    if not file.filename.endswith('.xlsx'):
        flash('Formato inválido. Solo se permiten archivos Excel (.xlsx)', 'danger')
        return _redirect_after_import()
        
    try:
        result = ClientService.bulk_import(file, current_user.id)
        
        if result['success_count'] > 0:
            flash(f"Se cargaron {result['success_count']} clientes exitosamente.", 'success')
            
        if result['errors']:
            # Display errors. Limit to first 10 to avoid huge flash messages if many fail
            error_msg = "No se pudieron cargar algunos clientes:<br>" + "<br>".join(result['errors'][:10])
            if len(result['errors']) > 10:
                error_msg += f"<br>... y {len(result['errors']) - 10} errores más."
            flash(error_msg, 'warning')
            
        if result['success_count'] == 0 and not result['errors']:
             flash("El archivo no contenía registros válidos o estaba vacío.", 'warning')

    except Exception as e:
        flash(f"Error crítico en la importación: {str(e)}", 'danger')
        
    return _redirect_after_import()

def _redirect_after_import():
    """Helper to redirect back to the correct dashboard based on role."""
    if current_user.rol == 'Analista':
        return redirect(url_for('analyst.analyst_dashboard'))
    elif current_user.rol == 'Aliado':
        return redirect(url_for('aliados.aliados_dashboard'))
    return redirect(url_for('admin.admin_dashboard'))
