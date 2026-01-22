from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, Client
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from utils.decorators import role_required
from utils.time_utils import get_colombia_now
from datetime import datetime


from services.payment_service import PaymentService
from models import Interaction

lawyer_bp = Blueprint('lawyer', __name__)

@lawyer_bp.route('/lawyer')
@login_required
@role_required(['Abogado', 'Admin'])
def lawyer_dashboard():

    
    query = Client.query.options(
        joinedload(Client.analista),
        joinedload(Client.abogado)
    ).filter(
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

    page = request.args.get('page', 1, type=int)
    page = request.args.get('page', 1, type=int)
    clients = query.paginate(page=page, per_page=20)
    
    # Fetch upcoming appointments
    upcoming_appointments = []
    if current_user.rol == 'Abogado':
        now = get_colombia_now()
        upcoming_appointments = Interaction.query.filter(
            Interaction.usuario_id == current_user.id,
            Interaction.tipo == 'Reunión Agendada',
            Interaction.fecha_hora_cita >= now
        ).order_by(Interaction.fecha_hora_cita.asc()).all()

    
    return render_template('lawyer/dashboard.html', clients=clients, upcoming_appointments=upcoming_appointments)

@lawyer_bp.route('/client/<int:client_id>/save_payment_diagnosis', methods=['POST'])
@login_required
@role_required(['Abogado', 'Aliado', 'Admin', 'Radicador'])
def save_payment_diagnosis(client_id):


    
    try:
        PaymentService.save_payment_diagnosis(client_id, request.form, user_rol=current_user.rol)
        flash('Información del diagnóstico actualizada', 'success')

    except Exception as e:
        flash(f'Error al guardar diagnóstico: {str(e)}', 'danger')
        
    return redirect(url_for('main.client_detail', client_id=client_id))

@lawyer_bp.route('/client/<int:client_id>/save_contract_details', methods=['POST'])
@login_required
@role_required(['Abogado', 'Aliado', 'Admin', 'Radicador'])
def save_contract_details(client_id):


    
    try:
        PaymentService.save_contract_details(client_id, request.form)
        flash('Contrato actualizado. Cuotas vacías eliminadas.', 'success')
    except Exception as e:
        flash(f'Error al guardar contrato: {str(e)}', 'danger')

    return redirect(url_for('main.client_detail', client_id=client_id))
