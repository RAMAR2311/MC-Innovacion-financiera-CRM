from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import login_required, current_user
from models import db, User, Client, AllyPayment
from werkzeug.utils import secure_filename
import os
from sqlalchemy import func
from utils.decorators import role_required
from services.client_service import ClientService
from services.payment_service import PaymentService


from datetime import datetime, date
import calendar

aliados_bp = Blueprint('aliados', __name__)

@aliados_bp.route('/aliados')
@login_required
@role_required(['Aliado', 'Admin'])
def aliados_dashboard():

    
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
    
    page = request.args.get('page', 1, type=int)
    clients = query.order_by(Client.created_at.desc()).paginate(page=page, per_page=20)

    
    return render_template('aliados/dashboard.html', 
                           clients=clients)

@aliados_bp.route('/aliados/new_client', methods=['GET', 'POST'])
@login_required
@role_required(['Aliado', 'Admin'])
def aliados_new_client():

    if request.method == 'POST':
        try:
            ClientService.create_client(request.form, current_user.id)
            flash('Cliente guardado', 'success')
            return redirect(url_for('aliados.aliados_dashboard'))
        except ValueError as e:
            flash(str(e), 'warning')
        except Exception as e:
            flash(f'Error al guardar cliente: {str(e)}', 'danger')

    return render_template('aliados/new_client.html')


@aliados_bp.route('/aliados/client/<int:client_id>/send_to_lawyer', methods=['POST'])
@login_required
@role_required(['Aliado'])
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
    print(f"Asunto: Nuevo caso asignado (Aliado) - {client.nombre}")
    print(f"Hola {lawyer.nombre_completo}, se te ha asignado un nuevo caso para revisión.")
    print(f"--------------------")
    
    flash(f'Caso enviado exitosamente al abogado {lawyer.nombre_completo}', 'success')
    return redirect(url_for('aliados.aliados_dashboard'))

@aliados_bp.route('/aliados/pagos')
@login_required
@role_required(['Aliado'])
def mis_pagos():

    
    pagos = AllyPayment.query.filter_by(ally_id=current_user.id).order_by(AllyPayment.created_at.desc()).all()
    return render_template('aliados/pagos.html', pagos=pagos)

@aliados_bp.route('/aliados/pagos/upload', methods=['POST'])
@login_required
@role_required(['Aliado'])
def upload_pago():

    try:
         file = request.files.get('file')
         observation = request.form.get('observation')
         PaymentService.save_ally_payment(file, observation, current_user.id)
         flash('Soporte de pago subido exitosamente', 'success')
    except ValueError as e:
         flash(str(e), 'danger')
    except Exception as e:
         flash(f'Error al subir pago: {str(e)}', 'danger')
    
    return redirect(url_for('aliados.mis_pagos'))


@aliados_bp.route('/aliados/pagos/download/<filename>')
@login_required
@role_required(['Aliado'])
def download_pago(filename):

         
    # Ensure user owns the file
    payment = AllyPayment.query.filter_by(filename=filename, ally_id=current_user.id).first()
    if not payment:
         flash('Archivo no encontrado o acceso denegado', 'danger')
         return redirect(url_for('aliados.mis_pagos'))

    upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'pagos_aliados')
    return send_from_directory(upload_folder, filename)
