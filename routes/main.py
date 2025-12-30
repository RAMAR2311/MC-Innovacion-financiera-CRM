from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app, jsonify, send_file
from flask_login import login_required, logout_user, current_user
from models import db, User, Client, Document, FinancialObligation, PaymentDiagnosis, ContractInstallment, AdministrativeExpense, CaseMessage, ClientNote
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from sqlalchemy import func
from xhtml2pdf import pisa
from io import BytesIO

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
        elif current_user.rol == 'Cliente':
            return redirect(url_for('main.client_portal'))
    return redirect(url_for('auth.login'))

@main_bp.route('/client/<int:client_id>')
@login_required
def client_detail(client_id):
    client = Client.query.get_or_404(client_id)

    if current_user.rol == 'Aliado' and client.analista_id != current_user.id:
        flash('No tienes permiso para acceder a este cliente.', 'danger')
        return redirect(url_for('aliados.aliados_dashboard'))
    
    if current_user.rol == 'Abogado' and client.abogado_id != current_user.id:
        flash('No tienes permiso para ver este expediente.', 'danger')
        return redirect(url_for('lawyer.lawyer_dashboard'))
    
    if current_user.rol == 'Analista' and client.analista_id != current_user.id:
        flash('No tienes permiso para ver este expediente.', 'danger')
        return redirect(url_for('analyst.analyst_dashboard'))
    
    # Mark messages as read if Abogado is viewing
    if current_user.rol == 'Abogado' and client.abogado_id == current_user.id:
        unread_msgs = CaseMessage.query.filter_by(client_id=client.id, is_read_by_recipient=False).all()
        for msg in unread_msgs:
            if msg.sender_id != current_user.id:
                msg.is_read_by_recipient = True
        db.session.commit()

    # Fetch chat history
    messages = CaseMessage.query.filter_by(client_id=client.id).order_by(CaseMessage.timestamp.asc()).all()

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
            
    # Fetch Notes
    notes = ClientNote.query.filter_by(client_id=client_id).order_by(ClientNote.timestamp.desc()).all()

    return render_template('client_detail.html', client=client, files=files, documents=documents, messages=messages, notes=notes)

@main_bp.route('/client/<int:client_id>/upload', methods=['POST'])
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

@main_bp.route('/uploads/<filename>')
@login_required
def download_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@main_bp.route('/client/<int:client_id>/update_status', methods=['POST'])
@login_required
def update_status(client_id):
    if current_user.rol not in ['Abogado', 'Admin']:
        flash('No autorizado', 'danger')
        return redirect(url_for('main.index'))
        
    client = Client.query.get_or_404(client_id)
    new_status = request.form.get('new_status')
    new_status = request.form.get('new_status')
    if new_status and new_status != client.estado:
        client.estado = new_status
        client.last_status_update = datetime.utcnow()
        db.session.commit()
        flash('Estado actualizado', 'success')
    return redirect(url_for('main.client_detail', client_id=client_id))

@main_bp.route('/document/<int:doc_id>/toggle_analyst_visibility', methods=['POST'])
@login_required
def toggle_analyst_visibility(doc_id):
    if current_user.rol not in ['Abogado', 'Admin']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    doc = Document.query.get_or_404(doc_id)
    doc.visible_para_analista = not doc.visible_para_analista
    db.session.commit()
    
    return jsonify({'success': True, 'visible': doc.visible_para_analista})

@main_bp.route('/document/<int:doc_id>/toggle_client_visibility', methods=['POST'])
@login_required
def toggle_client_visibility(doc_id):
    if current_user.rol not in ['Abogado', 'Admin']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    doc = Document.query.get_or_404(doc_id)
    doc.visible_para_cliente = not doc.visible_para_cliente
    db.session.commit()
    
    return jsonify({'success': True, 'visible': doc.visible_para_cliente})

@main_bp.route('/client/<int:client_id>/add_financial_obligation', methods=['POST'])
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

@main_bp.route('/client/<int:client_id>/update_analysis', methods=['POST'])
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

@main_bp.route('/obligation/<int:obligation_id>/update_legal_status', methods=['POST'])
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

@main_bp.route('/client/<int:client_id>/edit', methods=['POST'])
@login_required
def edit_client(client_id):
    if current_user.rol not in ['Admin', 'Abogado', 'Analista']:
        flash('No autorizado', 'danger')
        return redirect(url_for('main.index'))
    
    client = Client.query.get_or_404(client_id)
    
    # Security check again
    if current_user.rol == 'Abogado' and client.abogado_id != current_user.id:
        flash('No autorizado', 'danger')
        return redirect(url_for('main.index'))
    if current_user.rol == 'Analista' and client.analista_id != current_user.id:
        flash('No autorizado', 'danger')
        return redirect(url_for('main.index'))

    client.nombre = request.form.get('nombre')
    client.telefono = request.form.get('telefono')
    client.email = request.form.get('email')
    client.tipo_id = request.form.get('tipo_id')
    client.numero_id = request.form.get('numero_id')
    client.ciudad = request.form.get('ciudad')
    client.contract_number = request.form.get('contract_number')
    
    db.session.commit()
    flash('Información del cliente actualizada', 'success')
    return redirect(url_for('main.client_detail', client_id=client_id))

@main_bp.route('/client/<int:client_id>/add_note', methods=['POST'])
@login_required
def add_note(client_id):
    if current_user.rol not in ['Analista', 'Abogado', 'Admin']:
         flash('No autorizado', 'danger')
         return redirect(url_for('main.index'))
         
    content = request.form.get('note_content')
    if content:
        new_note = ClientNote(
            content=content,
            author_id=current_user.id,
            client_id=client_id
        )
        db.session.add(new_note)
        db.session.commit()
        flash('Nota agregada exitosamente', 'success')
    else:
        flash('La nota no puede estar vacía', 'warning')
        
    return redirect(url_for('main.client_detail', client_id=client_id))

@main_bp.route('/accounting')
@login_required
def accounting_dashboard():
    if current_user.rol not in ['Admin', 'Abogado']:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('main.index'))
    
    # Get Date Filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Base Queries
    # 1. KPIs
    q_income_diag = db.session.query(func.sum(PaymentDiagnosis.valor)).filter(PaymentDiagnosis.verificado == True)
    q_income_inst = db.session.query(func.sum(ContractInstallment.valor)).filter(ContractInstallment.estado == 'Pagada')
    
    # 3. Tables
    q_recent_diag = PaymentDiagnosis.query.filter_by(verificado=True)
    q_recent_inst = ContractInstallment.query

    # Apply Date Filters
    if start_date:
        q_income_diag = q_income_diag.filter(PaymentDiagnosis.fecha_pago >= start_date)
        q_income_inst = q_income_inst.filter(ContractInstallment.fecha_vencimiento >= start_date)
        q_recent_diag = q_recent_diag.filter(PaymentDiagnosis.fecha_pago >= start_date)
        q_recent_inst = q_recent_inst.filter(ContractInstallment.fecha_vencimiento >= start_date)
        
    if end_date:
        q_income_diag = q_income_diag.filter(PaymentDiagnosis.fecha_pago <= end_date)
        q_income_inst = q_income_inst.filter(ContractInstallment.fecha_vencimiento <= end_date)
        q_recent_diag = q_recent_diag.filter(PaymentDiagnosis.fecha_pago <= end_date)
        q_recent_inst = q_recent_inst.filter(ContractInstallment.fecha_vencimiento <= end_date)

    # Calculate KPIs
    income_diagnosis = q_income_diag.scalar() or 0
    income_installments = q_income_inst.scalar() or 0
    total_gross_income = income_diagnosis + income_installments
    
    # 2. Funnel Stats (Usually total, not filtered by date unless requested)
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
    
    # Execute Table Queries
    recent_diagnoses = q_recent_diag.order_by(PaymentDiagnosis.fecha_pago.desc()).limit(50).all()
    
    # Filter Installments Table by Status
    estado_filter = request.args.get('estado_cuota')
    if estado_filter and estado_filter != 'todos':
        q_recent_inst = q_recent_inst.filter_by(estado=estado_filter)
        
    recent_installments = q_recent_inst.order_by(ContractInstallment.fecha_vencimiento.desc()).limit(50).all()
    
    return render_template('accounting.html', 
                           income_diagnosis=income_diagnosis,
                           income_installments=income_installments,
                           total_gross_income=total_gross_income,
                           funnel_stats=funnel_stats,
                           recent_diagnoses=recent_diagnoses,
                           recent_installments=recent_installments,
                           current_filter=estado_filter,
                           start_date=start_date,
                           end_date=end_date)

@main_bp.route('/portal')
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
        return redirect(url_for('auth.login'))

    # Mark messages as read for Client
    unread_msgs = CaseMessage.query.filter_by(client_id=client.id, is_read_by_recipient=False).all()
    for msg in unread_msgs:
        if msg.sender_id != current_user.id:
            msg.is_read_by_recipient = True
    db.session.commit()

    # Fetch messages
    messages = CaseMessage.query.filter_by(client_id=client.id).order_by(CaseMessage.timestamp.asc()).all()
        
    contract = client.payment_contract
    total_pagado = 0
    progress_percentage = 0
    
    if contract:
        total_pagado = db.session.query(func.sum(ContractInstallment.valor)).filter(ContractInstallment.payment_contract_id == contract.id, ContractInstallment.estado == 'Pagada').scalar() or 0
        if contract.valor_total > 0:
            progress_percentage = (total_pagado / contract.valor_total) * 100
            
    documents = Document.query.filter_by(client_id=client.id).order_by(Document.created_at.desc()).all()

    return render_template('client_dashboard.html', client=client, contract=contract, total_pagado=total_pagado, progress_percentage=progress_percentage, documents=documents, messages=messages)

@main_bp.route('/balance_general', methods=['GET', 'POST'])
@login_required
def balance_general():
    if current_user.rol not in ['Admin', 'Abogado']:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('main.index'))

    # Date Filters
    start_date = request.args.get('start_date') or request.form.get('start_date')
    end_date = request.args.get('end_date') or request.form.get('end_date')

    # Handle POST (Bulk Save Expenses)
    if request.method == 'POST':
        saved_count = 0
        current_date_for_expense = datetime.now().date()
        if end_date:
             # Try to parse end_date to use it, otherwise use today
             try:
                 current_date_for_expense = datetime.strptime(end_date, '%Y-%m-%d').date()
             except:
                 pass

        for i in range(1, 11):
            desc = request.form.get(f'descripcion_{i}')
            val = request.form.get(f'valor_{i}')
            
            if desc and val:
                try:
                    val_float = float(val)
                    if val_float > 0:
                        new_expense = AdministrativeExpense(
                            descripcion=desc,
                            valor=val_float,
                            fecha=current_date_for_expense
                        )
                        db.session.add(new_expense)
                        saved_count += 1
                except ValueError:
                    continue # Skip invalid numbers
        
        if saved_count > 0:
            db.session.commit()
            flash(f'Se guardaron {saved_count} gastos exitosamente.', 'success')
        else:
            flash('No se detectaron datos válidos para guardar.', 'warning')
            
        return redirect(url_for('main.balance_general', start_date=start_date, end_date=end_date))

    # GET Logic - Calculations
    # 1. Total Income (Diagnoses + Installments)
    q_income_diag = db.session.query(func.sum(PaymentDiagnosis.valor)).filter(PaymentDiagnosis.verificado == True)
    q_income_inst = db.session.query(func.sum(ContractInstallment.valor)).filter(ContractInstallment.estado == 'Pagada')
    
    # 2. Expenses
    q_expenses = db.session.query(func.sum(AdministrativeExpense.valor))
    q_expenses_list = AdministrativeExpense.query

    # 3. Business Cost (Cost of diagnosis sold)
    q_diag_count = PaymentDiagnosis.query.filter_by(verificado=True)

    # Apply Filters
    if start_date:
        q_income_diag = q_income_diag.filter(PaymentDiagnosis.fecha_pago >= start_date)
        q_income_inst = q_income_inst.filter(ContractInstallment.fecha_vencimiento >= start_date)
        q_expenses = q_expenses.filter(AdministrativeExpense.fecha >= start_date)
        q_expenses_list = q_expenses_list.filter(AdministrativeExpense.fecha >= start_date)
        q_diag_count = q_diag_count.filter(PaymentDiagnosis.fecha_pago >= start_date)
        
    if end_date:
        q_income_diag = q_income_diag.filter(PaymentDiagnosis.fecha_pago <= end_date)
        q_income_inst = q_income_inst.filter(ContractInstallment.fecha_vencimiento <= end_date)
        q_expenses = q_expenses.filter(AdministrativeExpense.fecha <= end_date)
        q_expenses_list = q_expenses_list.filter(AdministrativeExpense.fecha <= end_date)
        q_diag_count = q_diag_count.filter(PaymentDiagnosis.fecha_pago <= end_date)

    total_ingresos = (q_income_diag.scalar() or 0) + (q_income_inst.scalar() or 0)
    total_gastos = q_expenses.scalar() or 0
    
    # Costo Negocio Calculation
    count_diag_sold = q_diag_count.count()
    costo_negocio = count_diag_sold * 32000
    
    utilidad_neta = total_ingresos - total_gastos - costo_negocio
    
    expenses_list = q_expenses_list.order_by(AdministrativeExpense.fecha.desc()).all()

    return render_template('balance_general.html',
                           total_ingresos=total_ingresos,
                           total_gastos=total_gastos,
                           costo_negocio=costo_negocio,
                           utilidad_neta=utilidad_neta,
                           expenses=expenses_list,
                           start_date=start_date,
                           end_date=end_date)
                           
@main_bp.route('/balance_general/pdf', methods=['GET'])
@login_required
def download_balance_pdf():
    if current_user.rol not in ['Admin', 'Abogado']:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('main.index'))

    # Date Filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Re-Calculate Logic (Identical to View)
    # 1. Income
    q_income_diag = db.session.query(func.sum(PaymentDiagnosis.valor)).filter(PaymentDiagnosis.verificado == True)
    q_income_inst = db.session.query(func.sum(ContractInstallment.valor)).filter(ContractInstallment.estado == 'Pagada')
    
    # 2. Expenses
    q_expenses = db.session.query(func.sum(AdministrativeExpense.valor))
    q_expenses_list = AdministrativeExpense.query
    
    # 3. Cost
    q_diag_count = PaymentDiagnosis.query.filter_by(verificado=True)

    # 4. Details for PDF table
    q_recent_diag = PaymentDiagnosis.query.filter_by(verificado=True)
    q_recent_inst = ContractInstallment.query.filter_by(estado='Pagada')

    if start_date:
        q_income_diag = q_income_diag.filter(PaymentDiagnosis.fecha_pago >= start_date)
        q_income_inst = q_income_inst.filter(ContractInstallment.fecha_vencimiento >= start_date)
        q_expenses = q_expenses.filter(AdministrativeExpense.fecha >= start_date)
        q_expenses_list = q_expenses_list.filter(AdministrativeExpense.fecha >= start_date)
        q_diag_count = q_diag_count.filter(PaymentDiagnosis.fecha_pago >= start_date)
        q_recent_diag = q_recent_diag.filter(PaymentDiagnosis.fecha_pago >= start_date)
        q_recent_inst = q_recent_inst.filter(ContractInstallment.fecha_vencimiento >= start_date)
        
    if end_date:
        q_income_diag = q_income_diag.filter(PaymentDiagnosis.fecha_pago <= end_date)
        q_income_inst = q_income_inst.filter(ContractInstallment.fecha_vencimiento <= end_date)
        q_expenses = q_expenses.filter(AdministrativeExpense.fecha <= end_date)
        q_expenses_list = q_expenses_list.filter(AdministrativeExpense.fecha <= end_date)
        q_diag_count = q_diag_count.filter(PaymentDiagnosis.fecha_pago <= end_date)
        q_recent_diag = q_recent_diag.filter(PaymentDiagnosis.fecha_pago <= end_date)
        q_recent_inst = q_recent_inst.filter(ContractInstallment.fecha_vencimiento <= end_date)

    total_ingresos = (q_income_diag.scalar() or 0) + (q_income_inst.scalar() or 0)
    total_gastos = q_expenses.scalar() or 0
    count_diag_sold = q_diag_count.count()
    costo_negocio = count_diag_sold * 32000
    utilidad_neta = total_ingresos - total_gastos - costo_negocio
    
    expenses_list = q_expenses_list.order_by(AdministrativeExpense.fecha.desc()).all()
    recent_diagnoses = q_recent_diag.order_by(PaymentDiagnosis.fecha_pago.desc()).limit(20).all()
    recent_installments = q_recent_inst.order_by(ContractInstallment.fecha_vencimiento.desc()).limit(20).all()

    # Render PDF Template
    html = render_template('balance_pdf.html',
                           total_ingresos=total_ingresos,
                           total_gastos=total_gastos,
                           costo_negocio=costo_negocio,
                           utilidad_neta=utilidad_neta,
                           expenses=expenses_list,
                           recent_diagnoses=recent_diagnoses,
                           recent_installments=recent_installments,
                           start_date=start_date,
                           end_date=end_date,
                           generation_date=datetime.now().strftime('%Y-%m-%d %H:%M'))
                           
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer)
    
    if pisa_status.err:
        return 'We had some errors <pre>' + html + '</pre>'
        
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f'Balance_General_{datetime.now().date()}.pdf', mimetype='application/pdf')
    
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
