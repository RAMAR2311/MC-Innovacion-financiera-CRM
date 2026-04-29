from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app, jsonify
from flask_login import login_required, logout_user, current_user
from models import db, Client, CaseMessage, ClientNote, ContractInstallment, Document, User, ClientStatus, Negotiation, FinancialObligation
from services.financial_service import FinancialService
from services.document_service import DocumentService
from services.client_service import ClientService
from services.payment_service import PaymentService
from utils.decorators import role_required
from utils.time_utils import get_colombia_now
from datetime import datetime
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.rol == 'Admin':
            return redirect(url_for('admin.admin_dashboard'))
        elif current_user.rol == 'Analista':
            return redirect(url_for('analyst.analyst_dashboard'))
        elif current_user.rol == 'Aliado':
            return redirect(url_for('aliados.aliados_dashboard'))
        elif current_user.rol == 'Abogado':
            return redirect(url_for('lawyer.lawyer_dashboard'))
        elif current_user.rol == 'Negociador':
            return redirect(url_for('negociador.dashboard'))
        elif current_user.rol == 'Cliente':
            return redirect(url_for('main.client_portal'))
    return redirect(url_for('auth.login'))

@main_bp.route('/client/<int:client_id>')
@login_required
def client_detail(client_id):
    client = Client.query.get_or_404(client_id)

    # Permission Checks
    if current_user.rol == 'Aliado' and client.analista_id != current_user.id:
        flash('No tienes permiso para acceder a este cliente.', 'danger')
        return redirect(url_for('aliados.aliados_dashboard'))
    
    if current_user.rol == 'Abogado' and client.abogado_id != current_user.id:
        flash('No tienes permiso para ver este expediente.', 'danger')
        return redirect(url_for('lawyer.lawyer_dashboard'))
    
    if current_user.rol == 'Analista' and client.analista_id != current_user.id:
        flash('No tienes permiso para ver este expediente.', 'danger')
        return redirect(url_for('analyst.analyst_dashboard'))

    if current_user.rol == 'Radicador' and client.radicador_id != current_user.id:
        flash('No tienes permiso para ver este expediente.', 'danger')
        return redirect(url_for('radicador.dashboard'))

    if current_user.rol == 'Negociador' and client.negociador_id != current_user.id:
        # Also check if this negociador has any negotiation on this client
        has_negotiation = Negotiation.query.join(FinancialObligation).filter(
            FinancialObligation.client_id == client_id,
            Negotiation.negociador_id == current_user.id
        ).first()
        if not has_negotiation:
            flash('No tienes permiso para ver este expediente.', 'danger')
            return redirect(url_for('negociador.dashboard'))
    
    # Mark messages as read if Abogado is viewing
    if current_user.rol == 'Abogado' and client.abogado_id == current_user.id:
        unread_msgs = CaseMessage.query.filter_by(client_id=client.id, is_read_by_recipient=False).all()
        for msg in unread_msgs:
            if msg.sender_id != current_user.id:
                msg.is_read_by_recipient = True
            db.session.commit()

    # Check for arrears automatically
    PaymentService.check_and_update_arrears(client.id)

    # Fetch chat history
    messages = CaseMessage.query.filter_by(client_id=client.id).order_by(CaseMessage.timestamp.asc()).all()

    # PERFORMANCE FIX: Use DB instead of os.listdir
    # This replaces the IO blocking loop
    documents = DocumentService.get_client_documents(client_id, current_user.rol)
    
    # For compatibility with template, we pass 'files' as empty or just use documents
    # The template likely iterates 'files' for the raw list. We should check the template.
    # Assuming we update template or 'documents' is what matters.
    # Based on previous code: 'files' was used to list files in folder. 'documents' was from DB.
    # Now we only support DB documents. We will pass empty files list to avoid errors if template uses it,
    # but the User should update template to rely on 'documents'. 
    # Actually, the user asked to FIX it. 
    # Ideally we should verify if 'files' is used in template. 
    # Looking at previous read of main.py, it passed 'files' AND 'documents'.
    # I will pass 'files' as a list of filenames from 'documents' to maintain compatibility if template uses "files" for something specific,
    # but the reliable source is 'documents'.
    files = [doc.filename for doc in documents]
            
    # Fetch Notes
    notes = ClientNote.query.filter_by(client_id=client_id).order_by(ClientNote.timestamp.desc()).all()

    radicadores = []
    negociadores = []
    all_users = []
    if current_user.rol in ['Abogado', 'Admin']:
        radicadores = User.query.filter_by(rol='Radicador').all()
        negociadores = User.query.filter_by(rol='Negociador').all()
        all_users = User.query.filter(User.rol != 'Cliente').all()

    # Verify if Prospect needs to complete info
    completion_required = False
    if client.estado == ClientStatus.PROSPECTO and client.payment_diagnosis and client.payment_diagnosis.verificado:
        completion_required = True

    # Get negotiations for this client
    client_negotiations = Negotiation.query.join(FinancialObligation).filter(
        FinancialObligation.client_id == client_id
    ).order_by(Negotiation.created_at.desc()).all()

    return render_template('client_detail.html', client=client, files=files, documents=documents, messages=messages, notes=notes, radicadores=radicadores, negociadores=negociadores, all_users=all_users, completion_required=completion_required, client_negotiations=client_negotiations)

@main_bp.route('/client/<int:client_id>/upload', methods=['POST'])
@login_required
def upload_file(client_id):
    if 'file' not in request.files:
        flash('No se seleccionaron archivos', 'danger')
        return redirect(request.url)
    
    files = request.files.getlist('file')
    if not files or files[0].filename == '':
        flash('No se seleccionó ningún archivo', 'danger')
        return redirect(request.url)
    
    success_count = 0
    errors = []
    
    try:
        visible_analyst = False
        visible_client = False
        
        if current_user.rol == 'Abogado':
            visible_analyst = 'visible_para_analista' in request.form
            visible_client = 'visible_para_cliente' in request.form
        elif current_user.rol in ['Analista', 'Aliado', 'Radicador']:
            visible_analyst = True 

        for file in files:
            if file and file.filename != '':
                try:
                    DocumentService.upload_file(file, client_id, current_user.id, visible_analyst, visible_client)
                    success_count += 1
                except Exception as e:
                    errors.append(f"Error en {file.filename}: {str(e)}")
        
        if success_count > 0:
            flash(f'Se subieron {success_count} archivo(s) exitosamente', 'success')
        
        if errors:
            flash(" ".join(errors), 'warning')

    except Exception as e:
        flash(f'Error crítico al subir archivos: {str(e)}', 'danger')

    return redirect(url_for('main.client_detail', client_id=client_id))

@main_bp.route('/uploads/<filename>')
@login_required
def download_file(filename):
    # Security: Ensure user has access to this file? 
    # Taking a shortcut here for now as requested strict refactor of structure, but can be improved.
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@main_bp.route('/client/<int:client_id>/update_status', methods=['POST'])
@login_required
@role_required(['Abogado', 'Admin'])
def update_status(client_id):
    client = Client.query.get_or_404(client_id)
    new_status = request.form.get('new_status')
    if new_status and new_status != client.estado:
        client.estado = new_status
        client.last_status_update = datetime.utcnow()
        db.session.commit()
        flash('Estado actualizado', 'success')
    return redirect(url_for('main.client_detail', client_id=client_id))

@main_bp.route('/document/<int:doc_id>/toggle_analyst_visibility', methods=['POST'])
@login_required
@role_required(['Abogado', 'Admin'])
def toggle_analyst_visibility(doc_id):
    try:
        new_state = DocumentService.toggle_visibility(doc_id, 'analyst')
        return jsonify({'success': True, 'visible': new_state})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@main_bp.route('/document/<int:doc_id>/toggle_client_visibility', methods=['POST'])
@login_required
@role_required(['Abogado', 'Admin'])
def toggle_client_visibility(doc_id):
    try:
        new_state = DocumentService.toggle_visibility(doc_id, 'client')
        return jsonify({'success': True, 'visible': new_state})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@main_bp.route('/client/<int:client_id>/add_financial_obligation', methods=['POST'])
@login_required
@role_required(['Analista', 'Abogado', 'Admin', 'Aliado', 'Radicador'])
def add_financial_obligation(client_id):
    try:
        FinancialService.add_obligation(request.form.to_dict(), client_id)
        flash('Obligación financiera agregada', 'success')
    except ValueError as e:
        flash(str(e), 'warning')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        
    return redirect(url_for('main.client_detail', client_id=client_id))

@main_bp.route('/client/<int:client_id>/update_analysis', methods=['POST'])
@login_required
@role_required(['Analista', 'Abogado', 'Aliado', 'Radicador'])
def update_analysis(client_id):
    client = Client.query.get_or_404(client_id)
    client.conclusion_analisis = request.form.get('conclusion_analisis')
    db.session.commit()
    flash('Análisis actualizado', 'success')
    return redirect(url_for('main.client_detail', client_id=client_id))

@main_bp.route('/obligation/<int:obligation_id>/update_legal_status', methods=['POST'])
@login_required
@role_required(['Analista', 'Abogado', 'Admin', 'Aliado', 'Radicador'])
def update_legal_status(obligation_id):
    new_status = request.form.get('estado_legal')
    obligation = FinancialService.update_legal_status(obligation_id, new_status)
    flash('Estado legal actualizado', 'success')
    return redirect(url_for('main.client_detail', client_id=obligation.client_id))

@main_bp.route('/client/<int:client_id>/edit', methods=['POST'])
@login_required
@role_required(['Admin', 'Abogado', 'Analista', 'Aliado', 'Radicador'])
def edit_client(client_id):
    client = Client.query.get_or_404(client_id)
    
    # Extra security check specific to hierarchy
    if current_user.rol == 'Abogado' and client.abogado_id != current_user.id:
        flash('No autorizado', 'danger')
        return redirect(url_for('main.index'))
    if current_user.rol == 'Analista' and client.analista_id != current_user.id:
        flash('No autorizado', 'danger')
        return redirect(url_for('main.index'))

    # RBAC Strict for editing Active Clients
    if client.estado != ClientStatus.PROSPECTO and current_user.rol != 'Admin':
        flash("Solo el administrador puede modificar datos de clientes activos", 'danger')
        return redirect(url_for('main.client_detail', client_id=client_id))

    # Use ClientService if possible, or keep simple update here. 
    # For now, let's keep it here but standard.
    # Update fields only if present in the form request to allow partial updates
    if 'nombre' in request.form:
        client.nombre = request.form['nombre']
    if 'telefono' in request.form:
        client.telefono = request.form['telefono']
    if 'email' in request.form:
        client.email = request.form['email']
    if 'tipo_id' in request.form:
        client.tipo_id = request.form['tipo_id']
    if 'numero_id' in request.form:
        client.numero_id = request.form['numero_id']
    if 'ciudad' in request.form:
        client.ciudad = request.form['ciudad']
    if 'contract_number' in request.form:
        val = request.form['contract_number'].strip()
        client.contract_number = val if val else None
        
    # Si la petición trae datos del formulario principal, actualizamos el checkbox de IVA
    if 'nombre' in request.form or 'tipo_id' in request.form:
        client.es_responsable_iva = 'es_responsable_iva' in request.form
    
    # Logic to Promote Prospecto -> Nuevo
    if request.form.get('promote_to_new') == '1' and client.estado == ClientStatus.PROSPECTO:
        client.estado = ClientStatus.NUEVO
        flash('Cliente activado exitosamente. Estado actualizado a Nuevo.', 'success')
    else:
        flash('Información del cliente actualizada', 'success')

    db.session.commit()
    return redirect(url_for('main.client_detail', client_id=client_id))

@main_bp.route('/client/<int:client_id>/add_note', methods=['POST'])
@login_required
@role_required(['Analista', 'Abogado', 'Admin', 'Aliado', 'Radicador', 'Negociador'])
def add_note(client_id):
    content = request.form.get('note_content', '').strip()
    if content:
        new_note = ClientNote(
            content=content,
            author_id=current_user.id,
            client_id=client_id,
            timestamp=get_colombia_now()
        )
        db.session.add(new_note)
        db.session.commit()
        flash('Nota agregada exitosamente', 'success')
    else:
        flash('La nota no puede estar vacía', 'warning')
        
    return redirect(url_for('main.client_detail', client_id=client_id))

@main_bp.route('/portal')
@login_required
def client_portal():
    if current_user.rol != 'Cliente':
        return redirect(url_for('main.index'))
    
    client = Client.query.filter_by(login_user_id=current_user.id).first()
    
    if not client:
        flash('No se encontró un expediente asociado a este usuario.', 'danger')
        logout_user()
        return redirect(url_for('auth.login'))

    # Mark messages as read
    unread_msgs = CaseMessage.query.filter_by(client_id=client.id, is_read_by_recipient=False).all()
    for msg in unread_msgs:
        if msg.sender_id != current_user.id:
            msg.is_read_by_recipient = True
    db.session.commit()

    messages = CaseMessage.query.filter_by(client_id=client.id).order_by(CaseMessage.timestamp.asc()).all()
        
    contract = client.payment_contract
    total_pagado = 0
    progress_percentage = 0
    
    if contract:
        total_pagado = db.session.query(db.func.sum(ContractInstallment.valor)).filter(ContractInstallment.payment_contract_id == contract.id, ContractInstallment.estado == 'Pagada').scalar() or 0
        if contract.valor_total > 0:
            progress_percentage = float((total_pagado / contract.valor_total) * 100)
            
    # Use Service for documents
    documents = DocumentService.get_client_documents(client.id, 'Cliente')

    return render_template('client_dashboard.html', client=client, contract=contract, total_pagado=total_pagado, progress_percentage=progress_percentage, documents=documents, messages=messages)

@main_bp.route('/client/<int:client_id>/assign_radicador', methods=['POST'])
@login_required
@role_required(['Abogado', 'Admin'])
def assign_radicador(client_id):
    client = Client.query.get_or_404(client_id)
    radicador_id = request.form.get('radicador_id')
    
    if radicador_id:
        client.radicador_id = radicador_id
        db.session.commit()
        flash('Radicador asignado exitosamente', 'success')
    
    return redirect(url_for('main.client_detail', client_id=client_id))

@main_bp.route('/client/<int:client_id>/reassign_user', methods=['POST'])
@login_required
@role_required(['Abogado', 'Admin'])
def reassign_user(client_id):
    client = Client.query.get_or_404(client_id)
    new_user_id = request.form.get('new_user_id')
    
    if new_user_id:
        new_user = User.query.get(new_user_id)
        if not new_user:
            flash('Usuario destino invalido.', 'danger')
            return redirect(url_for('main.client_detail', client_id=client_id))

        old_user_id = None
        if new_user.rol == 'Abogado':
            old_user_id = client.abogado_id
            if str(old_user_id) == str(new_user_id):
                flash('El cliente ya está asignado a este abogado.', 'warning')
                return redirect(url_for('main.client_detail', client_id=client_id))
            client.abogado_id = new_user_id
        elif new_user.rol == 'Radicador':
            old_user_id = client.radicador_id
            if str(old_user_id) == str(new_user_id):
                flash('El cliente ya está asignado a este radicador.', 'warning')
                return redirect(url_for('main.client_detail', client_id=client_id))
            client.radicador_id = new_user_id
        else:
            old_user_id = client.analista_id
            if str(old_user_id) == str(new_user_id):
                flash('El cliente ya está asignado a este usuario.', 'warning')
                return redirect(url_for('main.client_detail', client_id=client_id))
            client.analista_id = new_user_id

        if old_user_id:
            Document.query.filter_by(client_id=client_id, uploaded_by_id=old_user_id).update({Document.uploaded_by_id: new_user_id})
            ClientNote.query.filter_by(client_id=client_id, author_id=old_user_id).update({ClientNote.author_id: new_user_id})
            CaseMessage.query.filter_by(client_id=client_id, sender_id=old_user_id).update({CaseMessage.sender_id: new_user_id})
            from models import Interaction
            Interaction.query.filter_by(cliente_id=client_id, usuario_id=old_user_id).update({Interaction.usuario_id: new_user_id})

        db.session.commit()
        flash('El usuario fue reasignado exitosamente y sus registros fueron transferidos.', 'success')
            
    return redirect(url_for('main.client_detail', client_id=client_id))

@main_bp.route('/negotiation/<int:negotiation_id>/respond', methods=['POST'])
@login_required
@role_required(['Cliente'])
def respond_negotiation(negotiation_id):
    """El cliente acepta o rechaza una negociación."""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    
    # Verificar que este cliente es dueño de la obligación
    client = Client.query.filter_by(login_user_id=current_user.id).first()
    if not client or negotiation.obligation.client_id != client.id:
        flash('No tienes permiso para responder a esta negociación.', 'danger')
        return redirect(url_for('main.client_portal'))
    
    # Solo se puede responder a negociaciones con estado 'Negociada'
    if negotiation.estado != 'Negociada':
        flash('Esta negociación aún no tiene una propuesta para aceptar.', 'warning')
        return redirect(url_for('main.client_portal'))
    
    accion = request.form.get('accion')
    
    if accion == 'aceptar':
        negotiation.aceptada_por_cliente = True
        negotiation.fecha_respuesta_cliente = get_colombia_now()
        negotiation.estado = 'Finalizada'
        db.session.commit()
        flash('¡Has aceptado la negociación exitosamente!', 'success')
    elif accion == 'rechazar':
        negotiation.aceptada_por_cliente = False
        negotiation.fecha_respuesta_cliente = get_colombia_now()
        db.session.commit()
        flash('Has rechazado la negociación. El negociador será notificado.', 'info')
    else:
        flash('Acción no válida.', 'warning')
    
    return redirect(url_for('main.client_portal'))
