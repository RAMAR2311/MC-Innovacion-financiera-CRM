from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Client, Sale, Interaction, Installment, Document, FinancialObligation, PaymentDiagnosis, PaymentContract, ContractInstallment
from werkzeug.utils import secure_filename
import os
from datetime import datetime

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
    return redirect(url_for('main.login'))

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.password == password: # Insecure comparison for demo
            login_user(user)
            return redirect(url_for('main.index'))
        flash('Credenciales inválidas', 'danger')
    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

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

# --- Analista ---
@main.route('/analyst')
@login_required
def analyst_dashboard():
    if current_user.rol not in ['Analista', 'Admin']:
        return redirect(url_for('main.index'))
    
    search_query = request.args.get('search')
    if search_query:
        clients = Client.query.filter(
            (Client.nombre.contains(search_query)) | 
            (Client.numero_id.contains(search_query)) |
            (Client.telefono.contains(search_query))
        ).all()
    else:
        # Show recent clients or assigned clients
        clients = Client.query.order_by(Client.created_at.desc()).limit(20).all()
        
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
@main.route('/lawyer')
@login_required
def lawyer_dashboard():
    if current_user.rol not in ['Abogado', 'Admin']:
        return redirect(url_for('main.index'))
    clients = Client.query.filter(
        Client.estado.in_(['Pendiente_Analisis', 'Con_Analisis', 'Con_Contrato', 'Radicado', 'Finalizado'])
    ).all()
    return render_template('lawyer/dashboard.html', clients=clients)

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
        visible = False
        if current_user.rol == 'Abogado':
             visible = 'visible_para_analista' in request.form
        elif current_user.rol == 'Analista':
             visible = True # Analysts always see what they upload
             
        new_doc = Document(
            filename=filename,
            client_id=client_id,
            uploaded_by_id=current_user.id,
            visible_para_analista=visible
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

@main.route('/document/<int:doc_id>/toggle_visibility', methods=['POST'])
@login_required
def toggle_visibility(doc_id):
    if current_user.rol != 'Abogado':
        flash('No autorizado', 'danger')
        return redirect(url_for('main.index'))
        
    doc = Document.query.get_or_404(doc_id)
    doc.visible_para_analista = not doc.visible_para_analista
    db.session.commit()
    
    status_msg = "visible" if doc.visible_para_analista else "privado"
    flash(f'Documento ahora es {status_msg} para analistas', 'success')
    return redirect(url_for('main.client_detail', client_id=doc.client_id))

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
    if current_user.rol != 'Analista':
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
    
    try:
        contract.valor_total = float(request.form.get('valor_total') or 0)
    except ValueError:
        contract.valor_total = 0.0

    # Fixed 6 installments
    contract.numero_cuotas = 6
    
    db.session.add(contract)
    db.session.flush() # Get ID
    
    # Handle Installments - Clear and Recreate
    for inst in contract.installments:
        db.session.delete(inst)
        
    for i in range(1, 7):
        valor_str = request.form.get(f'cuota_{i}_valor')
        fecha_str = request.form.get(f'cuota_{i}_fecha')
        metodo = request.form.get(f'cuota_{i}_metodo')
        estado = request.form.get(f'cuota_{i}_estado')
        
        # Only save if we have at least a value or date or explicitly saving empty rows? 
        # User said: "save 6 quotas (even if empty...)"
        # So we save all 6 slots.
        
        try:
            val = float(valor_str) if valor_str else 0.0
        except ValueError:
            val = 0.0

        due_date = None
        if fecha_str:
            try:
                due_date = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        installment = ContractInstallment(
            payment_contract_id=contract.id,
            numero_cuota=i,
            valor=val,
            fecha_vencimiento=due_date,
            metodo_pago=metodo,
            estado=estado
        )
        db.session.add(installment)
        
    db.session.commit()
    flash('Contrato actualizado', 'success')
    return redirect(url_for('main.client_detail', client_id=client_id))
