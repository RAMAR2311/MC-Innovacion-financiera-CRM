from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Client, Sale, Interaction, Installment, Document, FinancialObligation, PaymentDiagnosis, PaymentContract, ContractInstallment, ChatMessage
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from sqlalchemy import func

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.rol == 'Admin':
            return redirect(url_for('main.admin_dashboard'))
        elif current_user.rol == 'Analista':
            return redirect(url_for('main.analyst_dashboard'))
        elif current_user.rol == 'Abogado':
            return redirect(url_for('main.lawyer_dashboard'))
        elif current_user.rol == 'Cliente':
            return redirect(url_for('main.client_portal'))
    return redirect(url_for('main.login'))

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.password == password: # Insecure comparison for demo
            login_user(user)
            if user.rol == 'Cliente':
                return redirect(url_for('main.client_portal'))
            elif user.rol == 'Admin':
                return redirect(url_for('main.admin_dashboard'))
            elif user.rol == 'Analista':
                return redirect(url_for('main.analyst_dashboard'))
            elif user.rol == 'Abogado':
                return redirect(url_for('main.lawyer_dashboard'))
            return redirect(url_for('main.index'))
        flash('Credenciales inválidas', 'danger')
    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not current_password or not new_password or not confirm_password:
            flash('Todos los campos son obligatorios.', 'warning')
        elif current_user.password != current_password:
            flash('La contraseña actual es incorrecta.', 'danger')
        elif new_password != confirm_password:
            flash('Las nuevas contraseñas no coinciden.', 'warning')
        else:
            current_user.password = new_password
            db.session.commit()
            flash('Contraseña actualizada exitosamente.', 'success')
            
            # Redirect based on role
            if current_user.rol == 'Cliente':
                return redirect(url_for('main.client_portal'))
            elif current_user.rol == 'Admin':
                return redirect(url_for('main.admin_dashboard'))
            elif current_user.rol == 'Analista':
                return redirect(url_for('main.analyst_dashboard'))
            elif current_user.rol == 'Abogado':
                return redirect(url_for('main.lawyer_dashboard'))
            return redirect(url_for('main.index'))

        # On error, redirect back to the previous page if possible, or default to index
        return redirect(request.referrer or url_for('main.index'))
    
    # If GET, just redirect to index as this is intended to be used via modal
    return redirect(url_for('main.index'))

# --- Admin ---
@main.route('/admin')
@login_required
def admin_dashboard():
    if current_user.rol != 'Admin':
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('main.index'))
    users = User.query.all()
    return render_template('admin/dashboard.html', users=users)

@main.route('/admin/create_user', methods=['POST'])
@login_required
def create_user():
    if current_user.rol != 'Admin':
        return redirect(url_for('main.index'))
    
    nombre = request.form.get('nombre')
    email = request.form.get('email')
    password = request.form.get('password')
    rol = request.form.get('rol')
    telefono = request.form.get('telefono')

    if User.query.filter_by(email=email).first():
        flash('El email ya existe', 'warning')
    else:
        new_user = User(nombre_completo=nombre, email=email, password=password, rol=rol, telefono=telefono)
        db.session.add(new_user)
        db.session.commit()
        flash('Usuario creado exitosamente', 'success')
    return redirect(url_for('main.admin_dashboard'))

@main.route('/client/<int:client_id>/generate_access', methods=['POST'])
@login_required
def generate_client_access(client_id):
    if current_user.rol != 'Admin':
        flash('No autorizado', 'danger')
        return redirect(url_for('main.index'))
    
    client = Client.query.get_or_404(client_id)
    email = client.email
    if not email:
        flash('El cliente no tiene un email registrado.', 'danger')
        return redirect(url_for('main.client_detail', client_id=client_id))

    # Auto-generate or set default password
    password = "Cliente2024*" 
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash(f'El usuario con email {email} ya existe.', 'warning')
        # Optional: Link if not linked? For now just warn.
        if not client.login_user_id:
             client.login_user_id = existing_user.id
             db.session.commit()
             flash('Se ha vinculado el usuario existente al cliente.', 'info')
        return redirect(url_for('main.client_detail', client_id=client_id))
    
    # Create new User
    # Note: In production use hashed passwords!
    new_user = User(
        nombre_completo=client.nombre,
        email=email,
        password=password, 
        rol='Cliente',
        telefono=client.telefono
    )
    db.session.add(new_user)
    db.session.flush() # to get ID
    
    # Link to Client
    client.login_user_id = new_user.id
    db.session.commit()
    
    flash(f'Usuario creado exitosamente. La contraseña temporal es: {password}', 'success')
    return redirect(url_for('main.client_detail', client_id=client_id))

# --- Analista ---
@main.route('/analyst')
@login_required
def analyst_dashboard():
    if current_user.rol not in ['Analista', 'Admin']:
        return redirect(url_for('main.index'))
    
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
        
    return render_template('analyst/dashboard.html', clients=clients)

@main.route('/analyst/new_client', methods=['GET', 'POST'])
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
        return redirect(url_for('main.analyst_dashboard'))
    return render_template('analyst/new_client.html')

@main.route('/client/<int:client_id>/send_to_lawyer', methods=['POST'])
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
    return redirect(url_for('main.analyst_dashboard'))

# --- Abogado ---
@main.route('/client/<int:client_id>/send_message', methods=['POST'])
@login_required
def send_message(client_id):
    data = request.get_json()
    message_text = data.get('message')
    
    if not message_text:
        return jsonify({'success': False, 'message': 'Mensaje vacío'}), 400
        
    client = Client.query.get_or_404(client_id)
    
    # Validation: Only involved users can chat
    if current_user.rol == 'Cliente' and client.login_user_id != current_user.id:
        return jsonify({'success': False, 'message': 'No autorizado'}), 403
    elif current_user.rol not in ['Abogado', 'Admin', 'Cliente']: # Analysts excluded for now? Prompt implied Lawyer and Client.
        return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
    msg = ChatMessage(
        client_id=client_id,
        sender_id=current_user.id,
        message=message_text,
        is_read=False
    )
    db.session.add(msg)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message_html': f'<div class="mb-2 text-end"><span class="d-inline-block p-2 rounded bg-primary text-white" style="max-width: 80%;">{msg.message}</span><small class="d-block text-muted" style="font-size: 0.7rem;">Ahora</small></div>'
    })

# --- Abogado ---
@main.route('/lawyer')
@login_required
def lawyer_dashboard():
    if current_user.rol not in ['Abogado', 'Admin']:
        return redirect(url_for('main.index'))
    
    query = Client.query.filter(
        Client.estado.in_(['Pendiente_Analisis', 'Con_Analisis', 'Con_Contrato', 'Radicado', 'Finalizado'])
    )

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
    
    # Calculate unread messages for each client
    # Dict {client_id: count}
    unread_counts = {}
    for client in clients:
        # Count messages sent by CLIENT (rol='Cliente') that are not read
        # Using a join or property check
        count = ChatMessage.query.join(User, ChatMessage.sender_id == User.id)\
            .filter(ChatMessage.client_id == client.id, User.rol == 'Cliente', ChatMessage.is_read == False).count()
        unread_counts[client.id] = count

    return render_template('lawyer/dashboard.html', clients=clients, unread_counts=unread_counts)

# --- Shared / Client Details ---
@main.route('/client/<int:client_id>')
@login_required
def client_detail(client_id):
    client = Client.query.get_or_404(client_id)
    
    # List files in upload folder for this client
    # We will create a subfolder per client or just prefix files
    # For simplicity, let's just list all files in uploads that start with client_id_
    files = []
    upload_folder = current_app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        
    for filename in os.listdir(upload_folder):
        if filename.startswith(f"client_{client_id}_"):
            files.append(filename)
            
    # Fetch documents from DB
    documents = Document.query.filter_by(client_id=client_id).all()
    
    # Filter for Analyst
    if current_user.rol == 'Analista':
        documents = [d for d in documents if d.visible_para_analista]

    # --- Chat Logic: Mark as Read ---
    if current_user.rol in ['Abogado', 'Admin']:
        # Mark messages from Client as read
        unread_msgs = ChatMessage.query.join(User).filter(
            ChatMessage.client_id == client.id, 
            User.rol == 'Cliente',
            ChatMessage.is_read == False
        ).all()
        
        if unread_msgs:
            for msg in unread_msgs:
                msg.is_read = True
            db.session.commit()
            
    return render_template('client_detail.html', client=client, files=files, documents=documents)

@main.route('/client/<int:client_id>/upload', methods=['POST'])
@login_required
def upload_file(client_id):
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(request.url)
    if file:
        filename = secure_filename(file.filename)
        # Prefix with client_id to associate
        filename = f"client_{client_id}_{filename}"
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        
        # Create Document record
        visible_analyst = False
        visible_client = False
        
        if current_user.rol == 'Abogado':
             visible_analyst = 'visible_para_analista' in request.form
             visible_client = 'visible_para_cliente' in request.form
        elif current_user.rol == 'Analista':
             visible_analyst = True # Analysts always see what they upload
             
        new_doc = Document(
            filename=filename,
            client_id=client_id,
            uploaded_by_id=current_user.id,
            visible_para_analista=visible_analyst,
            visible_para_cliente=visible_client
        )
        db.session.add(new_doc)
        db.session.commit()
        
        flash('Archivo subido exitosamente', 'success')
        return redirect(url_for('main.client_detail', client_id=client_id))

@main.route('/uploads/<filename>')
@login_required
def download_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@main.route('/client/<int:client_id>/update_status', methods=['POST'])
@login_required
def update_status(client_id):
    if current_user.rol not in ['Abogado', 'Admin']:
        flash('No autorizado', 'danger')
        return redirect(url_for('main.index'))
        
    client = Client.query.get_or_404(client_id)
    new_status = request.form.get('new_status')
    if new_status:
        client.estado = new_status
        db.session.commit()
        flash('Estado actualizado', 'success')
    return redirect(url_for('main.client_detail', client_id=client_id))

@main.route('/document/<int:doc_id>/toggle_analyst_visibility', methods=['POST'])
@login_required
def toggle_analyst_visibility(doc_id):
    if current_user.rol not in ['Abogado', 'Admin']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    doc = Document.query.get_or_404(doc_id)
    doc.visible_para_analista = not doc.visible_para_analista
    db.session.commit()
    
    return jsonify({'success': True, 'visible': doc.visible_para_analista})

@main.route('/document/<int:doc_id>/toggle_client_visibility', methods=['POST'])
@login_required
def toggle_client_visibility(doc_id):
    if current_user.rol not in ['Abogado', 'Admin']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    doc = Document.query.get_or_404(doc_id)
    doc.visible_para_cliente = not doc.visible_para_cliente
    db.session.commit()
    
    return jsonify({'success': True, 'visible': doc.visible_para_cliente})

@main.route('/client/<int:client_id>/add_financial_obligation', methods=['POST'])
@login_required
def add_financial_obligation(client_id):
    if current_user.rol not in ['Analista', 'Abogado', 'Admin']:
        flash('No autorizado', 'danger')
        return redirect(url_for('main.index'))
        
    entidad = request.form.get('entidad')
    estado = request.form.get('estado')
    valor = request.form.get('valor')
    estado_legal = request.form.get('estado_legal')
    
    if entidad and estado and valor:
        new_obligation = FinancialObligation(
            client_id=client_id,
            entidad=entidad,
            estado=estado,
            valor=float(valor),
            estado_legal=estado_legal if estado_legal else 'Sin Iniciar'
        )
        db.session.add(new_obligation)
        db.session.commit()
        flash('Obligación financiera agregada', 'success')
    else:
        flash('Todos los campos son obligatorios', 'warning')
        
    return redirect(url_for('main.client_detail', client_id=client_id))

@main.route('/client/<int:client_id>/update_analysis', methods=['POST'])
@login_required
def update_analysis(client_id):
    if current_user.rol not in ['Analista', 'Abogado']:
        flash('No autorizado', 'danger')
        return redirect(url_for('main.index'))
        
    client = Client.query.get_or_404(client_id)
    conclusion = request.form.get('conclusion_analisis')
    
    client.conclusion_analisis = conclusion
    db.session.commit()
    flash('Análisis actualizado', 'success')
    
    return redirect(url_for('main.client_detail', client_id=client_id))

@main.route('/obligation/<int:obligation_id>/update_legal_status', methods=['POST'])
@login_required
def update_legal_status(obligation_id):
    if current_user.rol not in ['Analista', 'Abogado', 'Admin']:
        flash('No autorizado', 'danger')
        return redirect(url_for('main.index'))
        
    obligation = FinancialObligation.query.get_or_404(obligation_id)
    new_status = request.form.get('estado_legal')
    
    if new_status:
        obligation.estado_legal = new_status
        db.session.commit()
        flash('Estado legal actualizado', 'success')
        
    return redirect(url_for('main.client_detail', client_id=obligation.client_id))

@main.route('/client/<int:client_id>/save_payment_diagnosis', methods=['POST'])
@login_required
def save_payment_diagnosis(client_id):
    if current_user.rol != 'Abogado':
        flash('No autorizado', 'danger')
        return redirect(url_for('main.index'))
    
    client = Client.query.get_or_404(client_id)
    payment = client.payment_diagnosis or PaymentDiagnosis(client_id=client.id)
    
    payment.valor = float(request.form.get('valor') or 0)
    payment.fecha_pago = datetime.strptime(request.form.get('fecha_pago'), '%Y-%m-%d').date() if request.form.get('fecha_pago') else None
    payment.metodo_pago = request.form.get('metodo_pago')
    payment.verificado = 'verificado' in request.form
    
    db.session.add(payment)
    db.session.commit()
    
    flash('Información del diagnóstico actualizada', 'success')
    return redirect(url_for('main.client_detail', client_id=client_id))

@main.route('/client/<int:client_id>/save_contract_details', methods=['POST'])
@login_required
def save_contract_details(client_id):
    if current_user.rol != 'Abogado':
        flash('No autorizado', 'danger')
        return redirect(url_for('main.index'))
    
    client = Client.query.get_or_404(client_id)
    contract = client.payment_contract or PaymentContract(client_id=client.id)
    
    # Ensure contract has ID if it's new
    if not contract.id:
        db.session.add(contract)
        db.session.flush()

    try:
        contract.valor_total = float(request.form.get('valor_total') or 0)
    except ValueError:
        contract.valor_total = 0.0

    # Updated Logic: Fixed 6 slots, filter by validity
    
    # Map existing installments
    # Refresh installments from DB if needed or access relationship
    current_insts = {i.numero_cuota: i for i in contract.installments}
    
    # Valid Installments Count (for contract.numero_cuotas)
    valid_count = 0

    for i in range(1, 7): # Forever 6 loops
        valor_str = request.form.get(f'cuota_{i}_valor')
        fecha_str = request.form.get(f'cuota_{i}_fecha')
        metodo = request.form.get(f'cuota_{i}_metodo')
        estado = request.form.get(f'cuota_{i}_estado')
        
        try:
            val = float(valor_str) if valor_str else 0.0
        except ValueError:
            val = 0.0
            
        # validity check: Must have a status or value > 0 to be considered "real"
        # User said: "Solo debe crear... SI el usuario seleccionó un Estado válido... y puso un Valor."
        is_valid = (estado in ['Pendiente', 'Pagada', 'En Mora']) and (val > 0)
        
        inst = current_insts.get(i)
        
        if is_valid:
            valid_count += 1
            if not inst:
                # FIX: Use relationship object instead of ID to avoid integrity error if ID not set
                inst = ContractInstallment(payment_contract=contract, numero_cuota=i)
                db.session.add(inst)
            
            # Update fields
            inst.valor = val
            inst.metodo_pago = metodo
            inst.estado = estado
            
            if fecha_str:
                try:
                    inst.fecha_vencimiento = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                except ValueError:
                    inst.fecha_vencimiento = None
            else:
                inst.fecha_vencimiento = None
                
        else:
            # If not valid but exists in DB, delete it (clean up)
            if inst:
                db.session.delete(inst)

    # Update total quotas count based on valid ones? Or keeping it separate? 
    # For now, let's update it so it reflects reality.
    contract.numero_cuotas = valid_count 
    
    db.session.commit()
    flash('Contrato actualizado. Cuotas vacías eliminadas.', 'success')
    return redirect(url_for('main.client_detail', client_id=client_id))

# --- Accounting ---
@main.route('/accounting')
@login_required
def accounting_dashboard():
    if current_user.rol not in ['Admin', 'Abogado']:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('main.index'))
    
    # 1. KPIs
    # Ingresos por Diagnósticos: Suma de PaymentDiagnosis.valor donde verificado sea True.
    income_diagnosis = db.session.query(func.sum(PaymentDiagnosis.valor)).filter(PaymentDiagnosis.verificado == True).scalar() or 0
    
    # Ingresos por Cuotas: Suma de ContractInstallment.valor donde estado sea 'Pagada'.
    income_installments = db.session.query(func.sum(ContractInstallment.valor)).filter(ContractInstallment.estado == 'Pagada').scalar() or 0
    
    total_gross_income = income_diagnosis + income_installments
    
    # 2. Funnel Stats
    # Conteo de Clientes por Estado
    clients_with_analysis = Client.query.filter_by(estado='Con_Analisis').count()
    clients_with_contract = Client.query.filter_by(estado='Con_Contrato').count()
    clients_radicados = Client.query.filter_by(estado='Radicado').count()
    clients_finalized = Client.query.filter_by(estado='Finalizado').count()
    
    funnel_stats = {
        'Con_Analisis': clients_with_analysis,
        'Con_Contrato': clients_with_contract,
        'Radicado': clients_radicados,
        'Finalizado': clients_finalized
    }
    
    # 3. Tables
    # Tabla 1: Últimos Diagnósticos Pagados
    recent_diagnoses = PaymentDiagnosis.query.filter_by(verificado=True).order_by(PaymentDiagnosis.fecha_pago.desc()).limit(50).all()
    
    # Tabla 2: Historial de Cuotas (con Filtro)
    estado_filter = request.args.get('estado_cuota')
    
    query = ContractInstallment.query
    if estado_filter and estado_filter != 'todos':
        query = query.filter_by(estado=estado_filter)
        
    recent_installments = query.order_by(ContractInstallment.fecha_vencimiento.desc()).limit(50).all()
    
    return render_template('accounting.html', 
                           income_diagnosis=income_diagnosis,
                           income_installments=income_installments,
                           total_gross_income=total_gross_income,
                           funnel_stats=funnel_stats,
                           recent_diagnoses=recent_diagnoses,
                           recent_installments=recent_installments,
                           current_filter=estado_filter)

# --- Client Portal ---
@main.route('/portal')
@login_required
def client_portal():
    if current_user.rol != 'Cliente':
        # Safety fallback
        return redirect(url_for('main.index'))
    
    # Securely fetch the client associated with the current user
    client = Client.query.filter_by(login_user_id=current_user.id).first()
    
    if not client:
        flash('No se encontró un expediente asociado a este usuario.', 'danger')
        logout_user()
        return redirect(url_for('main.login'))
    
    # Calculate Data
    contract = client.payment_contract
    total_pagado = 0
    if contract and contract.installments:
        total_pagado = db.session.query(func.sum(ContractInstallment.valor)).filter(
            ContractInstallment.payment_contract_id == contract.id,
            ContractInstallment.estado == 'Pagada'
        ).scalar() or 0
        
    contract_total = contract.valor_total if contract else 0
    progress_percentage = 0
    if contract_total > 0:
        progress_percentage = (total_pagado / contract_total) * 100

    # Fetch documents visible for client
    documents = Document.query.filter_by(client_id=client.id, visible_para_cliente=True).all()

    return render_template('client_dashboard.html', client=client, contract=contract, total_pagado=total_pagado, progress_percentage=progress_percentage, documents=documents)
