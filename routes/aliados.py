from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import login_required, current_user
from models import db, User, Client, AllyPayment
from werkzeug.utils import secure_filename
import os
from sqlalchemy import func
from datetime import datetime, date
import calendar

aliados_bp = Blueprint('aliados', __name__)

@aliados_bp.route('/aliados')
@login_required
def aliados_dashboard():
    if current_user.rol not in ['Aliado', 'Admin']:
        return redirect(url_for('main.index'))
    
    nombre = request.args.get('nombre')
    analista = request.args.get('analista')
    fecha = request.args.get('fecha')

    query = Client.query

    if current_user.rol == 'Aliado':
        query = query.filter(Client.analista_id == current_user.id)
    
    if nombre:
        query = query.filter(Client.nombre.ilike(f'%{nombre}%'))
    
    if analista: # This filter might be redundant for Aliado if they can only see theirs, but kept for Admin
        query = query.join(Client.analista).filter(User.nombre_completo.ilike(f'%{analista}%'))
    
    if fecha:
        query = query.filter(func.date(Client.created_at) == fecha)
    
    clients = query.order_by(Client.created_at.desc()).all()
    
    return render_template('aliados/dashboard.html', 
                           clients=clients)

@aliados_bp.route('/aliados/new_client', methods=['GET', 'POST'])
@login_required
def aliados_new_client():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        tipo_id = request.form.get('tipo_id')
        numero_id = request.form.get('numero_id')
        email = request.form.get('email')
        ciudad = request.form.get('ciudad')
        motivo_consulta = request.form.get('motivo_consulta')
        contract_number = request.form.get('contract_number')
        
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
            contract_number=contract_number,
            email=email,
            ciudad=ciudad,
            motivo_consulta=motivo_consulta,
            estado=estado, 
            analista_id=current_user.id
        )
        db.session.add(client)
        db.session.commit()
        flash('Cliente guardado', 'success')
        return redirect(url_for('aliados.aliados_dashboard'))
    return render_template('aliados/new_client.html')

@aliados_bp.route('/aliados/client/<int:client_id>/send_to_lawyer', methods=['POST'])
@login_required
def send_to_lawyer(client_id):
    if current_user.rol != 'Aliado':
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
    print(f"Asunto: Nuevo caso asignado (Aliado) - {client.nombre}")
    print(f"Hola {lawyer.nombre_completo}, se te ha asignado un nuevo caso para revisión.")
    print(f"--------------------")
    
    flash(f'Caso enviado exitosamente al abogado {lawyer.nombre_completo}', 'success')
    return redirect(url_for('aliados.aliados_dashboard'))

@aliados_bp.route('/aliados/pagos')
@login_required
def mis_pagos():
    if current_user.rol != 'Aliado':
        return redirect(url_for('main.index'))
    
    pagos = AllyPayment.query.filter_by(ally_id=current_user.id).order_by(AllyPayment.created_at.desc()).all()
    return render_template('aliados/pagos.html', pagos=pagos)

@aliados_bp.route('/aliados/pagos/upload', methods=['POST'])
@login_required
def upload_pago():
    if current_user.rol != 'Aliado':
        return redirect(url_for('main.index'))
    
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo', 'danger')
        return redirect(url_for('aliados.mis_pagos'))
        
    file = request.files['file']
    observation = request.form.get('observation')
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'danger')
        return redirect(url_for('aliados.mis_pagos'))
        
    if file and file.filename.lower().endswith('.pdf'):
        filename = secure_filename(file.filename)
        # Prefix with user id and timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{current_user.id}_{timestamp}_{filename}"
        
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'pagos_aliados')
        if not os.path.exists(upload_folder):
             os.makedirs(upload_folder)
             
        file.save(os.path.join(upload_folder, filename))
        
        new_payment = AllyPayment(
            filename=filename,
            observation=observation,
            ally_id=current_user.id
        )
        db.session.add(new_payment)
        db.session.commit()
        
        flash('Soporte de pago subido exitosamente', 'success')
    else:
        flash('Solo se permiten archivos PDF', 'danger')
        
    return redirect(url_for('aliados.mis_pagos'))

@aliados_bp.route('/aliados/pagos/download/<filename>')
@login_required
def download_pago(filename):
    if current_user.rol != 'Aliado':
         return redirect(url_for('main.index'))
         
    # Ensure user owns the file
    payment = AllyPayment.query.filter_by(filename=filename, ally_id=current_user.id).first()
    if not payment:
         flash('Archivo no encontrado o acceso denegado', 'danger')
         return redirect(url_for('aliados.mis_pagos'))

    upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'pagos_aliados')
    return send_from_directory(upload_folder, filename)
