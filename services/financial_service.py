from models import db, PaymentDiagnosis, ContractInstallment, AdministrativeExpense, Client, Sale, PaymentContract, FinancialObligation
from sqlalchemy import func
from datetime import datetime
from sqlalchemy.orm import joinedload

class FinancialService:
    @staticmethod
    def calculate_taxes(valor_base, es_responsable_iva=False):
        """
        Calculates taxes given a base value and depending on whether the client pays taxes.
        Returns a dictionary with the breakdown.
        """
        valor_base = float(valor_base or 0)
        
        if not es_responsable_iva:
            return {
                'base': valor_base,
                'iva': 0.0,
                'retefuente': 0.0,
                'ica': 0.0,
                'total': valor_base
            }
        
        iva = valor_base * 0.19
        retefuente = valor_base * 0.025
        ica = valor_base * 0.01104
        total = valor_base + iva
        
        return {
            'base': valor_base,
            'iva': iva,
            'retefuente': retefuente,
            'ica': ica,
            'total': total
        }

    @staticmethod
    def get_balance_general(start_date=None, end_date=None):
        """
        Calculates general balance KPIs and retrieves filtered data for financial reports.
        """
        # Validate Dates
        import calendar
        from datetime import date
        
        if not start_date or start_date in ['None', '', 'null']:
            today = date.today()
            start_date = f"{today.year}-{today.month:02d}-01"
            
        if not end_date or end_date in ['None', '', 'null']:
            today = date.today()
            last_day = calendar.monthrange(today.year, today.month)[1]
            end_date = f"{today.year}-{today.month:02d}-{last_day}"

        from models import Expense
        # Tarjeta 3: Ventas Totales
        # Diagnósticos
        q_income_diag_total = db.session.query(func.sum(PaymentDiagnosis.valor)).filter(
            PaymentDiagnosis.verificado == True,
            PaymentDiagnosis.fecha_pago >= start_date,
            PaymentDiagnosis.fecha_pago <= end_date
        ).scalar() or 0.0
        
        # Contratos (Proxy: The contract's first installment falls in the date range)
        q_contracts_total = db.session.query(func.sum(PaymentContract.valor_total)).join(ContractInstallment).filter(
            ContractInstallment.numero_cuota == 1,
            ContractInstallment.fecha_vencimiento >= start_date,
            ContractInstallment.fecha_vencimiento <= end_date
        ).scalar() or 0.0
        
        ventas_totales = float(q_income_diag_total) + float(q_contracts_total)

        # Calculo de Gastos en el rango
        # Para DateTime, necesitamos que el end_date cubra todo el día hasta las 23:59:59
        end_date_str = f"{end_date} 23:59:59"

        q_expenses_indirect = db.session.query(func.sum(Expense.valor_base)).filter(
            Expense.tipo == 'Costo Indirecto',
            Expense.fecha >= start_date,
            Expense.fecha <= end_date_str
        ).scalar() or 0.0
        
        q_expenses_operative = db.session.query(func.sum(Expense.valor_base)).filter(
            Expense.tipo == 'Gasto Operativo',
            Expense.fecha >= start_date,
            Expense.fecha <= end_date_str
        ).scalar() or 0.0

        # Tarjeta 1: Costos Totales
        count_diag_sold = PaymentDiagnosis.query.filter(
            PaymentDiagnosis.verificado == True,
            PaymentDiagnosis.fecha_pago >= start_date,
            PaymentDiagnosis.fecha_pago <= end_date
        ).count()
        
        costos_totales = (count_diag_sold * 35000.0) + float(q_expenses_indirect)

        # Tarjeta 2: Gastos Administrativos
        gastos_administrativos = float(q_expenses_operative)

        # Tax calculations helpers (Para Tarjeta 4)
        q_tax_diag_base = db.session.query(func.sum(PaymentDiagnosis.valor)).join(Client).filter(
            PaymentDiagnosis.verificado == True, Client.es_responsable_iva == True,
            PaymentDiagnosis.fecha_pago >= start_date,
            PaymentDiagnosis.fecha_pago <= end_date
        )
        q_tax_inst_base = db.session.query(func.sum(ContractInstallment.valor)).join(PaymentContract).join(Client).filter(
            ContractInstallment.estado == 'Pagada', Client.es_responsable_iva == True,
            ContractInstallment.fecha_vencimiento >= start_date,
            ContractInstallment.fecha_vencimiento <= end_date
        )

        base_taxable = (q_tax_diag_base.scalar() or 0) + (q_tax_inst_base.scalar() or 0)
        base_taxable = float(base_taxable)
        
        total_iva = base_taxable * 0.19
        total_retefuente = base_taxable * 0.025
        total_ica = base_taxable * 0.01104
        
        # Tarjeta 4: Impuestos de Clientes
        impuestos_clientes = total_iva + total_retefuente + total_ica

        # Re-calc variables compatibility
        total_ingresos = float(db.session.query(func.sum(PaymentDiagnosis.valor)).filter(PaymentDiagnosis.verificado == True, PaymentDiagnosis.fecha_pago >= start_date, PaymentDiagnosis.fecha_pago <= end_date).scalar() or 0) + float(db.session.query(func.sum(ContractInstallment.valor)).filter(ContractInstallment.estado == 'Pagada', ContractInstallment.fecha_vencimiento >= start_date, ContractInstallment.fecha_vencimiento <= end_date).scalar() or 0)
        costo_negocio = count_diag_sold * 35000.0
        utilidad_neta = ventas_totales - (costos_totales + gastos_administrativos + impuestos_clientes)
        
        q_recent_diag = PaymentDiagnosis.query.options(joinedload(PaymentDiagnosis.client)).filter(
            PaymentDiagnosis.verificado == True,
            PaymentDiagnosis.fecha_pago >= start_date,
            PaymentDiagnosis.fecha_pago <= end_date
        )
        q_recent_inst = ContractInstallment.query.options(joinedload(ContractInstallment.payment_contract).joinedload(PaymentContract.client)).filter(
            ContractInstallment.estado == 'Pagada',
            ContractInstallment.fecha_vencimiento >= start_date,
            ContractInstallment.fecha_vencimiento <= end_date
        )
        
        return {
            'total_ingresos': total_ingresos,
            'costo_negocio': costo_negocio,
            'utilidad_neta': utilidad_neta,
            'ventas_totales': ventas_totales,
            'ventas_diagnosticos': float(q_income_diag_total),
            'ventas_contratos': float(q_contracts_total),
            'income_diagnosis': float(q_income_diag_total), # Backward compatibility for accounting
            'income_installments': total_ingresos - float(q_income_diag_total), # Backward compatibility
            'costos_totales': costos_totales,
            'costos_directos': count_diag_sold * 35000.0,
            'costos_indirectos': float(q_expenses_indirect),
            'gastos_administrativos': gastos_administrativos,
            'impuestos_clientes': impuestos_clientes,
            'q_recent_diag': q_recent_diag,     # Query object for pagination
            'q_recent_inst': q_recent_inst,     # Query object for pagination
            'q_expenses_list': None,            # Removed query
            'total_gross_income': total_ingresos,
            'total_iva': total_iva,
            'total_retefuente': total_retefuente,
            'total_ica': total_ica,
            'start_date_used': start_date,
            'end_date_used': end_date
        }

    @staticmethod
    def get_expense_summary(start_date=None, end_date=None):
        from models import Expense  # Import local para evitar circular imports si es necesario
        
        q_diag_count = PaymentDiagnosis.query.filter_by(verificado=True)
        q_expenses = Expense.query
        
        if start_date:
            q_diag_count = q_diag_count.filter(PaymentDiagnosis.fecha_pago >= start_date)
            q_expenses = q_expenses.filter(Expense.fecha >= start_date)
        if end_date:
            q_diag_count = q_diag_count.filter(PaymentDiagnosis.fecha_pago <= end_date)
            end_date_str = f"{end_date} 23:59:59"
            q_expenses = q_expenses.filter(Expense.fecha <= end_date_str)
            
        diagnoses_count = q_diag_count.count()
        costos_directos = diagnoses_count * 35000.0
        
        # Calcular sumas de Costos Indirectos y Gastos Operativos
        costos_indirectos = 0.0
        gastos_operativos = 0.0
        
        expenses_list = q_expenses.all()
        for exp in expenses_list:
            total_val = (exp.valor_base or 0) + (exp.valor_impuesto or 0)
            if exp.tipo == 'Costo Indirecto':
                costos_indirectos += total_val
            elif exp.tipo == 'Gasto Operativo':
                gastos_operativos += total_val
                
        return {
            'costos_directos': costos_directos,
            'costos_indirectos': costos_indirectos,
            'gastos_operativos': gastos_operativos,
            'total_gastos': costos_directos + costos_indirectos + gastos_operativos,
            'q_expenses_list': q_expenses # Query object para paginación si se necesita
        }

    @staticmethod
    def get_funnel_stats(start_date=None, end_date=None):
        query = Client.query
        
        if start_date:
            query = query.filter(Client.created_at >= start_date)
        if end_date:
            end_date_str = f"{end_date} 23:59:59"
            query = query.filter(Client.created_at <= end_date_str)

        clients_with_analysis = query.filter_by(estado='Con_Analisis').count()
        clients_with_contract = query.filter_by(estado='Con_Contrato').count()
        clients_radicados = query.filter_by(estado='Radicado').count()
        clients_finalized = query.filter_by(estado='Finalizado').count()
        
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

    @staticmethod
    def delete_obligation(obligation_id):
        """
        Deletes a financial obligation record.
        """
        obligation = FinancialObligation.query.get_or_404(obligation_id)
        db.session.delete(obligation)
        db.session.commit()
        return True
