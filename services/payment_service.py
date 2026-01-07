from models import db, Client, PaymentDiagnosis, PaymentContract, ContractInstallment, AllyPayment
from typing import Dict, Any
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from flask import current_app


class PaymentService:
    @staticmethod
    def save_payment_diagnosis(client_id: int, data: Dict[str, Any], user_rol: str = None) -> None:
        """
        Saves or updates payment diagnosis information.
        """
        client = Client.query.get_or_404(client_id)
        payment = client.payment_diagnosis or PaymentDiagnosis(client_id=client.id)
        
        try:
            payment.valor = float(data.get('valor') or 0)
        except ValueError:
            payment.valor = 0.0

        fecha_pago_str = data.get('fecha_pago')
        if fecha_pago_str:
             try:
                payment.fecha_pago = datetime.strptime(fecha_pago_str, '%Y-%m-%d').date()
             except ValueError:
                 payment.fecha_pago = None
        else:
            payment.fecha_pago = None

        metodo_raw = data.get('metodo_pago') or ''
        payment.metodo_pago = metodo_raw.replace('\r', '').replace('\n', '').strip() if metodo_raw else None

        # Security: Only Admin/Abogado can modify 'verificado'
        if user_rol in ['Admin', 'Abogado']:
            # Fix for PostgreSQL: Convert checkbox 'on' to boolean True
            payment.verificado = data.get('verificado') == 'on'
        # if user_rol is Aliado or Analista, we stay with current value (or default False)

        
        db.session.add(payment)
        db.session.commit()

    @staticmethod
    def save_contract_details(client_id: int, data: Dict[str, Any]) -> None:
        """
        Saves or updates contract details, managing dynamic installments (N quotas).
        """
        client = Client.query.get_or_404(client_id)
        contract = client.payment_contract or PaymentContract(client_id=client.id)
        
        # Ensure contract has ID if it's new
        if not contract.id:
            db.session.add(contract)
            db.session.flush()

        try:
            contract.valor_total = float(data.get('valor_total') or 0)
        except ValueError:
            contract.valor_total = 0.0

        # Updated Logic: Dynamic N slots
        
        # 1. Identify all indices present in the form data
        # keys look like cuota_{i}_valor, cuota_{i}_fecha, etc.
        form_indices = set()
        for key in data.keys():
            if key.startswith('cuota_') and '_valor' in key:
                parts = key.split('_')
                if len(parts) >= 3 and parts[1].isdigit():
                    form_indices.add(int(parts[1]))

        # 2. Map existing installments from DB for easy access
        current_insts = {i.numero_cuota: i for i in contract.installments}
        
        valid_count = 0
        
        # 3. Process form data indices
        for i in form_indices:
            valor_str = data.get(f'cuota_{i}_valor')
            fecha_str = data.get(f'cuota_{i}_fecha')
            metodo = data.get(f'cuota_{i}_metodo')
            estado = data.get(f'cuota_{i}_estado')
            
            try:
                val = float(valor_str) if valor_str else 0.0
            except ValueError:
                val = 0.0
            
            # Validity check: Must have a status or value > 0
            is_valid = (estado in ['Pendiente', 'Pagada', 'En Mora', 'Anulada']) and (val > 0)
            
            inst = current_insts.get(i)
            
            if is_valid:
                valid_count += 1
                if not inst:
                    inst = ContractInstallment(payment_contract=contract, numero_cuota=i)
                    db.session.add(inst)
                
                inst.valor = val
                # Capture new concept/description field and clean inputs
                concepto_raw = data.get(f'cuota_{i}_concepto') or ''
                inst.concepto = concepto_raw.replace('\r', '').replace('\n', '').strip() if concepto_raw else None
                
                metodo_raw = metodo or ''
                inst.metodo_pago = metodo_raw.replace('\r', '').replace('\n', '').strip() if metodo_raw else None
                inst.estado = estado

                
                if fecha_str:
                    try:
                        inst.fecha_vencimiento = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    except ValueError:
                        inst.fecha_vencimiento = None
                else:
                    inst.fecha_vencimiento = None
            else:
                # If invalid but existed, delete it
                if inst:
                    db.session.delete(inst)

        # 4. Cleanup: Delete DB installments that were NOT in the form data (removed by user)
        for i, inst in current_insts.items():
            if i not in form_indices:
                db.session.delete(inst)

        # Update total quotas count
        contract.numero_cuotas = valid_count 
        
        db.session.commit()

    @staticmethod
    def save_ally_payment(file, observation: str, ally_id: int) -> None:
        """
        Saves a payment proof file uploaded by an ally.
        """
        if not file or file.filename == '':
            raise ValueError('No se seleccionó ningún archivo')
        
        if not file.filename.lower().endswith('.pdf'):
             raise ValueError('Solo se permiten archivos PDF')

        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{ally_id}_{timestamp}_{filename}"

        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'pagos_aliados')
        if not os.path.exists(upload_folder):
             os.makedirs(upload_folder)

        file.save(os.path.join(upload_folder, filename))

        new_payment = AllyPayment(
            filename=filename,
            observation=observation,
            ally_id=ally_id
        )
        db.session.add(new_payment)
        db.session.commit()
