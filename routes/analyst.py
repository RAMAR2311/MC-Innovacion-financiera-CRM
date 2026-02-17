from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, Client
from sqlalchemy import func, or_
from utils.decorators import role_required


analyst_bp = Blueprint('analyst', __name__)

from datetime import datetime, date
import calendar

@analyst_bp.route('/analyst')
@login_required
@role_required(['Analista', 'Admin'])
def analyst_dashboard():

    
    # Logic for Monthly Goal Progress
    now = datetime.now()
    _, last_day = calendar.monthrange(now.year, now.month)
    first_date = date(now.year, now.month, 1)
    last_date = date(now.year, now.month, last_day)

    # Approved/Advanced States
    approved_states = [
        'Análisis Realizado', 'Con_Analisis', 'Con_Contrato', 
        'Radicado', 'Finalizado', 'Finalizado_Exitoso', 'Cerrado_Pago'
    ]
    # Note: 'Análisis Realizado' might be a legacy string, keeping it just in case, 
    # but based on previous logs 'Con_Analisis' seems to be the key.
    
    # Calculate Progress: Clients belonging to current user, created this month, in advanced state
    progreso = Client.query.filter(
        Client.analista_id == current_user.id,
        Client.created_at >= first_date,
        Client.created_at <= last_date,
        Client.estado.in_(approved_states)
    ).count()
    
    meta = 64
    porcentaje = min((progreso / meta) * 100, 100) if meta > 0 else 0

    nombre = request.args.get('nombre')
    status = request.args.get('status')
    fecha = request.args.get('fecha')

    query = Client.query

    if current_user.rol == 'Analista':
        query = query.filter(Client.analista_id == current_user.id)

    if nombre:
        search_term = f'%{nombre}%'
        query = query.filter(
            or_(
                Client.nombre.ilike(search_term),
                Client.telefono.ilike(search_term),
                Client.numero_id.ilike(search_term)
            )
        )
    
    if status:
        query = query.filter(Client.estado == status)
    
    if fecha:
        query = query.filter(func.date(Client.created_at) == fecha)
    
    page = request.args.get('page', 1, type=int)
    clients = query.order_by(Client.created_at.desc()).paginate(page=page, per_page=20)

        
    return render_template('analyst/dashboard.html', 
                           clients=clients,
                           progreso=progreso,
                           meta=meta,
                           porcentaje=porcentaje)

from services.client_service import ClientService

@analyst_bp.route('/analyst/new_client', methods=['GET', 'POST'])
@login_required
@role_required(['Analista', 'Admin'])
def new_client():

    if request.method == 'POST':
        try:
            # Prepare data dictionary, including the 'incomplete' flag existence check
            data = request.form.to_dict()
            if 'incomplete' in request.form:
                data['incomplete'] = True
                
            ClientService.create_client(data, current_user.id)
            flash('Cliente guardado exitosamente', 'success')
            return redirect(url_for('analyst.analyst_dashboard'))
            
        except ValueError as e:
            flash(str(e), 'danger')
            # Fallback: Render template again, potentially with preserved data 
            # (Simplest is just flash error for now)
            return render_template('analyst/new_client.html')
        except Exception as e:
             flash(f"Error inesperado: {str(e)}", 'danger')
             return render_template('analyst/new_client.html')

    return render_template('analyst/new_client.html')

@analyst_bp.route('/client/<int:client_id>/send_to_lawyer', methods=['POST'])
@login_required
@role_required(['Analista'])
def send_to_lawyer(client_id):

    
    client = Client.query.get_or_404(client_id)
    
    # Logic to find a lawyer (simple assignment: first available)
    lawyer = User.query.filter_by(rol='Abogado').first()
    
    if not lawyer:
        flash('No hay abogados disponibles para asignar el caso.', 'warning')
        return redirect(url_for('main.client_detail', client_id=client_id))
        
    client.estado = 'Pendiente_Analisis'
    client.abogado_id = lawyer.id
    db.session.commit()
    
    # Simulation of email notification
    print(f"--- NOTIFICACIÓN ---")
    print(f"Para: {lawyer.email}")
    print(f"Asunto: Nuevo caso asignado - {client.nombre}")
    print(f"Hola {lawyer.nombre_completo}, se te ha asignado un nuevo caso para revisión.")
    print(f"--------------------")
    
    flash(f'Caso enviado exitosamente al abogado {lawyer.nombre_completo}', 'success')
    return redirect(url_for('analyst.analyst_dashboard'))
