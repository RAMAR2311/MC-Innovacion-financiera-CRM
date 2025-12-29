from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, Client
from sqlalchemy import func

analyst_bp = Blueprint('analyst', __name__)

from datetime import datetime, date
import calendar

@analyst_bp.route('/analyst')
@login_required
def analyst_dashboard():
    if current_user.rol not in ['Analista', 'Admin']:
        return redirect(url_for('main.index'))
    
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

    # Existing Search Logic
    nombre = request.args.get('nombre')
    analista = request.args.get('analista')
    fecha = request.args.get('fecha')

    query = Client.query

    if nombre:
        query = query.filter(Client.nombre.ilike(f'%{nombre}%'))
    
    if analista:
        query = query.join(Client.analista).filter(User.nombre_completo.ilike(f'%{analista}%'))
    
    if fecha:
        query = query.filter(func.date(Client.created_at) == fecha)
    
    clients = query.order_by(Client.created_at.desc()).all()
        
    return render_template('analyst/dashboard.html', 
                           clients=clients,
                           progreso=progreso,
                           meta=meta,
                           porcentaje=porcentaje)

@analyst_bp.route('/analyst/new_client', methods=['GET', 'POST'])
@login_required
def new_client():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        tipo_id = request.form.get('tipo_id')
        numero_id = request.form.get('numero_id')
        email = request.form.get('email')
        ciudad = request.form.get('ciudad')
        motivo_consulta = request.form.get('motivo_consulta')
        
        # Lógica para "Información Incompleta" vs "Nuevo"
        if 'incomplete' in request.form:
            estado = 'Informacion_Incompleta'
        else:
            estado = 'Nuevo'
            
        client = Client(
            nombre=nombre, 
            telefono=telefono, 
            tipo_id=tipo_id,
            numero_id=numero_id,
            email=email,
            ciudad=ciudad,
            motivo_consulta=motivo_consulta,
            estado=estado, 
            analista_id=current_user.id
        )
        db.session.add(client)
        db.session.commit()
        flash('Cliente guardado', 'success')
        return redirect(url_for('analyst.analyst_dashboard'))
    return render_template('analyst/new_client.html')

@analyst_bp.route('/client/<int:client_id>/send_to_lawyer', methods=['POST'])
@login_required
def send_to_lawyer(client_id):
    if current_user.rol != 'Analista':
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('main.index'))
    
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
