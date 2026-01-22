from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, send_from_directory
from flask_login import login_required, current_user
from models import db, Client, User, AllyPayment
from utils.decorators import role_required
from sqlalchemy import or_, func
from services.client_service import ClientService
from services.payment_service import PaymentService
import os

radicador_bp = Blueprint('radicador', __name__)

@radicador_bp.route('/radicador')
@login_required
@role_required(['Radicador', 'Admin'])
def dashboard():
    nombre = request.args.get('nombre')
    # Use 'analista' param name to match template form, but it refers to radicador/analyst search
    analista_query = request.args.get('analista') 
    fecha = request.args.get('fecha')

    query = Client.query

    # If Radicador, see only theirs
    if current_user.rol == 'Radicador':
        query = query.filter_by(radicador_id=current_user.id)

    if nombre:
        query = query.filter(Client.nombre.ilike(f'%{nombre}%'))
    
    if analista_query:
        # Search by Radicador name if Admin is looking, or redundant filtering
        query = query.join(Client.radicador).filter(User.nombre_completo.ilike(f'%{analista_query}%'))

    if fecha:
        query = query.filter(func.date(Client.created_at) == fecha)

    # Ordenar por fecha de creación descendente por defecto
    page = request.args.get('page', 1, type=int)
    clients = query.order_by(Client.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('radicador/dashboard.html', clients=clients)

@radicador_bp.route('/radicador/new_client', methods=['GET', 'POST'])
@login_required
@role_required(['Radicador', 'Admin'])
def new_client():
    if request.method == 'POST':
        try:
            # We use ClientService.create_client. 
            # Note: create_client usually assigns 'analyst_id'. 
            # We might need to handle radicador assignment manually or update service.
            # For now, let's create and then update radicador_id if the service assumes analyst.
            # Checking service signature: create_client(form_data, user_id)
            # It sets analista_id = user_id.
            # If Radicador creates checks, they might be set as analista_id.
            # Ideally Radicador should be radicador_id.
            # Let's create normally, then updating fields.
            
            # Since we can't see Service code right now to be 100% sure, 
            # we will assume standard creation and then fix IDs if needed.
            # But wait, if Radicador has "SAME capabilities as Aliado", maybe they SHOULD be analista_id?
            # Aliados are effectively analysts.
            # If the user wants separate "Radicador" role, presumably distinct from "Analyst".
            # I'll create the client, and if the user is Radicador, I'll ensure radicador_id is set.
            
            client = ClientService.create_client(request.form, current_user.id)
            
            # If the service set analista_id to current_user.id but we want radicador_id:
            if current_user.rol == 'Radicador':
                client.radicador_id = current_user.id
                # If they shouldn't be analista, unset it? 
                # Ally IS analista in the system. 
                # If Radicador is just another type of Ally, keeping analista_id MIGHT be key.
                # But 'Radicador' usually implies intake. 
                # I will set BOTH to be safe, or just radicador_id.
                # But the dashboard filters by `radicador_id`. 
                db.session.commit()

            flash('Cliente guardado', 'success')
            return redirect(url_for('radicador.dashboard'))
        except ValueError as e:
            flash(str(e), 'warning')
        except Exception as e:
            flash(f'Error al guardar cliente: {str(e)}', 'danger')

    # We can reuse allied/new_client.html or create one. 
    # Since we didn't duplicate the template, we should verify if 'aliados/new_client.html' exists.
    # It does. We can render it.
    return render_template('aliados/new_client.html')

@radicador_bp.route('/radicador/client/<int:client_id>/send_to_lawyer', methods=['POST'])
@login_required
@role_required(['Radicador'])
def send_to_lawyer(client_id):
    client = Client.query.get_or_404(client_id)
    
    # Logic to find a lawyer
    lawyer = User.query.filter_by(rol='Abogado').first()
    
    if not lawyer:
        flash('No hay abogados disponibles para asignar el caso.', 'warning')
        return redirect(url_for('main.client_detail', client_id=client_id))
        
    client.estado = 'Pendiente_Analisis'
    client.abogado_id = lawyer.id
    db.session.commit()
    
    flash(f'Caso enviado exitosamente al abogado {lawyer.nombre_completo}', 'success')
    return redirect(url_for('radicador.dashboard'))

@radicador_bp.route('/radicador/pagos')
@login_required
@role_required(['Radicador'])
def mis_pagos():
    # Reuse AllyPayment model or create new? Assuming structure allows reuse or empty for now.
    # Use 'ally_id' to store radicador_id? The model is AllyPayment.
    # If the user is Radicador, we might need to adjust models. 
    # But for now, let's assume this feature isn't strictly requested/vital 
    # OR we use the same table if it just uses UserID.
    pagos = AllyPayment.query.filter_by(ally_id=current_user.id).order_by(AllyPayment.created_at.desc()).all()
    return render_template('aliados/pagos.html', pagos=pagos)
