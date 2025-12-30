from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, Client, PaymentDiagnosis, PaymentContract, ContractInstallment
from sqlalchemy import func
from datetime import datetime

lawyer_bp = Blueprint('lawyer', __name__)

@lawyer_bp.route('/lawyer')
@login_required
def lawyer_dashboard():
    if current_user.rol not in ['Abogado', 'Admin']:
        return redirect(url_for('main.index'))
    
    query = Client.query.filter(
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

    clients = query.all()
    
    return render_template('lawyer/dashboard.html', clients=clients)

@lawyer_bp.route('/client/<int:client_id>/save_payment_diagnosis', methods=['POST'])
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

@lawyer_bp.route('/client/<int:client_id>/save_contract_details', methods=['POST'])
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
