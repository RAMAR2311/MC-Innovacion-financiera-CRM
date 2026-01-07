from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, Client
from sqlalchemy import func
from services.payment_service import PaymentService

lawyer_bp = Blueprint('lawyer', __name__)

@lawyer_bp.route('/lawyer')
@login_required
def lawyer_dashboard():
    if current_user.rol not in ['Abogado', 'Admin']:
        return redirect(url_for('main.index'))
    
    query = Client.query.filter(
        Client.estado.in_(['Pendiente_Analisis', 'Con_Analisis', 'Con_Contrato', 'Radicado', 'Finalizado', 'Finalizado_Proceso_Credito'])
    )

    if current_user.rol == 'Abogado':
        query = query.filter(Client.abogado_id == current_user.id)

    # Filtering logic
    nombre = request.args.get('nombre')
    analista = request.args.get('analista')
    fecha = request.args.get('fecha')

    if nombre:
        query = query.filter((Client.nombre.ilike(f'%{nombre}%')) | (Client.numero_id.ilike(f'%{nombre}%')))
    
    if analista:
        query = query.join(Client.analista).filter(User.nombre_completo.ilike(f'%{analista}%'))
    
    if fecha:
        # Cast created_at to date for comparison
        query = query.filter(func.date(Client.created_at) == fecha)

    clients = query.all()
    
    return render_template('lawyer/dashboard.html', clients=clients)

@lawyer_bp.route('/client/<int:client_id>/save_payment_diagnosis', methods=['POST'])
@login_required
def save_payment_diagnosis(client_id):
    if current_user.rol not in ['Abogado', 'Aliado', 'Analista', 'Admin']:
        flash('No autorizado', 'danger')
        return redirect(url_for('main.index'))

    
    try:
        PaymentService.save_payment_diagnosis(client_id, request.form, user_rol=current_user.rol)
        flash('Información del diagnóstico actualizada', 'success')

    except Exception as e:
        flash(f'Error al guardar diagnóstico: {str(e)}', 'danger')
        
    return redirect(url_for('main.client_detail', client_id=client_id))

@lawyer_bp.route('/client/<int:client_id>/save_contract_details', methods=['POST'])
@login_required
def save_contract_details(client_id):
    if current_user.rol not in ['Abogado', 'Aliado', 'Analista', 'Admin']:
        flash('No autorizado', 'danger')
        return redirect(url_for('main.index'))

    
    try:
        PaymentService.save_contract_details(client_id, request.form)
        flash('Contrato actualizado. Cuotas vacías eliminadas.', 'success')
    except Exception as e:
        flash(f'Error al guardar contrato: {str(e)}', 'danger')

    return redirect(url_for('main.client_detail', client_id=client_id))
