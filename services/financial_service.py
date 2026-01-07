from models import db, PaymentDiagnosis, ContractInstallment, AdministrativeExpense, Client, Sale, PaymentContract, FinancialObligation
from sqlalchemy import func
from datetime import datetime
from sqlalchemy.orm import joinedload

class FinancialService:
    @staticmethod
    def get_balance_general(start_date=None, end_date=None):
        """
        Calculates general balance KPIs and retrieves filtered data for financial reports.
        """
        # Validate Dates
        if start_date in ['None', '', 'null']: start_date = None
        if end_date in ['None', '', 'null']: end_date = None

        # Base Queries
        # 1. KPIs
        q_income_diag = db.session.query(func.sum(PaymentDiagnosis.valor)).filter(PaymentDiagnosis.verificado == True)
        q_income_inst = db.session.query(func.sum(ContractInstallment.valor)).filter(ContractInstallment.estado == 'Pagada')
        
        # Expenses
        q_expenses = db.session.query(func.sum(AdministrativeExpense.valor))
        q_expenses_list = AdministrativeExpense.query

        # Count of diagnoses for cost calculation
        q_diag_count = PaymentDiagnosis.query.filter_by(verificado=True)

        # 3. Tables (Optimized with joinedload)
        q_recent_diag = PaymentDiagnosis.query.options(joinedload(PaymentDiagnosis.client)).filter_by(verificado=True)
        q_recent_inst = ContractInstallment.query.options(joinedload(ContractInstallment.payment_contract).joinedload(PaymentContract.client)).filter_by(estado='Pagada')


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
        
        # Don't execute queries here unless necessary, return query objects or data as needed
        # For this service, we return raw query objects for tables to allow pagination in controller
        # OR execute them if the controller expects list.
        # Given the previous logic, let's return query objects for paginated tables, and values for KPIs.
        
        return {
            'total_ingresos': total_ingresos,
            'total_gastos': total_gastos,
            'costo_negocio': costo_negocio,
            'utilidad_neta': utilidad_neta,
            'q_recent_diag': q_recent_diag,     # Query object for pagination
            'q_recent_inst': q_recent_inst,     # Query object for pagination
            'q_expenses_list': q_expenses_list, # Query object for pagination
            'income_diagnosis': q_income_diag.scalar() or 0,       # Added for accounting dashboard
            'income_installments': q_income_inst.scalar() or 0,    # Added for accounting dashboard
            'total_gross_income': total_ingresos                   # Added for accounting dashboard
        }

    @staticmethod
    def get_funnel_stats():
        clients_with_analysis = Client.query.filter_by(estado='Con_Analisis').count()
        clients_with_contract = Client.query.filter_by(estado='Con_Contrato').count()
        clients_radicados = Client.query.filter_by(estado='Radicado').count()
        clients_finalized = Client.query.filter_by(estado='Finalizado').count()
        
        return {
            'Con_Analisis': clients_with_analysis,
            'Con_Contrato': clients_with_contract,
            'Radicado': clients_radicados,
            'Finalizado': clients_finalized
        }

    @staticmethod
    def add_obligation(data, client_id):
        """
        Adds a new financial obligation to a client.
        """
        entidad = data.get('entidad', '').replace('\r', '').replace('\n', '').strip()
        estado = data.get('estado', '').replace('\r', '').replace('\n', '').strip()
        valor = data.get('valor')
        estado_legal = data.get('estado_legal', '').replace('\r', '').replace('\n', '').strip()

        if not (entidad and estado and valor):
            raise ValueError("Todos los campos son obligatorios")

        new_obligation = FinancialObligation(
            client_id=client_id,
            entidad=entidad,
            estado=estado,
            valor=float(valor),
            estado_legal=estado_legal if estado_legal else 'Sin Iniciar'
        )
        db.session.add(new_obligation)
        db.session.commit()
        return new_obligation

    @staticmethod
    def update_legal_status(obligation_id, new_status):
        """
        Updates the legal status of a financial obligation.
        """
        obligation = FinancialObligation.query.get_or_404(obligation_id)
        if new_status:
            obligation.estado_legal = new_status
            db.session.commit()
            return obligation
        return None
