from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from flask_login import current_user, login_required
from services.financial_service import FinancialService
from services.pdf_service import PDFService
from models import PaymentDiagnosis, ContractInstallment, AdministrativeExpense, db
from utils.decorators import role_required
from datetime import datetime
import hashlib
import os

financial_bp = Blueprint('financial', __name__)

@financial_bp.route('/accounting')
@login_required
@role_required(['Admin', 'Abogado'])
def accounting_dashboard():
    # Get Date Filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Get Data from Service
    data = FinancialService.get_balance_general(start_date, end_date)
    funnel_stats = FinancialService.get_funnel_stats()

    # Pagination for Diagnoses
    page_diag = request.args.get('page_diag', 1, type=int)
    recent_diagnoses = data['q_recent_diag'].order_by(PaymentDiagnosis.fecha_pago.desc()).paginate(page=page_diag, per_page=20)

    # Filter Installments Table by Status
    estado_filter = request.args.get('estado_cuota')
    q_recent_inst = data['q_recent_inst']
    if estado_filter and estado_filter != 'todos':
        q_recent_inst = q_recent_inst.filter_by(estado=estado_filter)
        
    # Pagination for Installments
    page_inst = request.args.get('page_inst', 1, type=int)
    recent_installments = q_recent_inst.order_by(ContractInstallment.fecha_vencimiento.desc()).paginate(page=page_inst, per_page=20)
    
    return render_template('accounting.html', 
                           income_diagnosis=data['income_diagnosis'],
                           income_installments=data['income_installments'],
                           total_gross_income=data['total_gross_income'],
                           funnel_stats=funnel_stats,
                           recent_diagnoses=recent_diagnoses,
                           recent_installments=recent_installments,
                           current_filter=estado_filter,
                           start_date=start_date,
                           end_date=end_date)


@financial_bp.route('/balance_general', methods=['GET', 'POST'])
@login_required
@role_required(['Admin', 'Abogado'])
def balance_general():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Handle New Expense Submission
    if request.method == 'POST':
        try:
            saved_count = 0
            # Determine date context
            current_date_for_expense = datetime.now().date()
            if end_date:
                try:
                    current_date_for_expense = datetime.strptime(end_date, '%Y-%m-%d').date()
                except ValueError:
                    pass

            for i in range(1, 6):
                desc = request.form.get(f'descripcion_{i}')
                val = request.form.get(f'valor_{i}')
                fecha_input = request.form.get(f'fecha_{i}') 

                if desc and val:
                    try:
                        val_float = float(val)
                        if val_float > 0:
                            # Determine date
                            expense_date = current_date_for_expense
                            if fecha_input:
                                try:
                                    expense_date = datetime.strptime(fecha_input, '%Y-%m-%d').date()
                                except ValueError:
                                    pass
                            
                            new_expense = AdministrativeExpense(
                                descripcion=desc,
                                valor=val_float,
                                fecha=expense_date
                            )
                            db.session.add(new_expense)
                            saved_count += 1
                    except ValueError:
                        continue
            
            if saved_count > 0:
                db.session.commit()
                flash(f'{saved_count} gastos registrados exitosamente.', 'success')
            else:
                flash('No se registraron gastos válidos.', 'warning')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar gastos: {str(e)}', 'danger')
            
        return redirect(url_for('financial.balance_general', start_date=start_date, end_date=end_date))

    # Get Data
    data = FinancialService.get_balance_general(start_date, end_date)
    
    # Pagination for Expenses
    page = request.args.get('page', 1, type=int)
    expenses = data['q_expenses_list'].order_by(AdministrativeExpense.fecha.desc()).paginate(page=page, per_page=20)

    return render_template('balance_general.html',
                           total_ingresos=data['total_ingresos'],
                           total_gastos=data['total_gastos'],
                           costo_negocio=data['costo_negocio'],
                           utilidad_neta=data['utilidad_neta'],
                           expenses=expenses,
                           start_date=start_date,
                           end_date=end_date)


@financial_bp.route('/balance_general/pdf')
@login_required
@role_required(['Admin', 'Abogado'])
def download_balance_pdf():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Hash params for caching
    params_str = f"{start_date}_{end_date}"
    params_hash = hashlib.md5(params_str.encode()).hexdigest()

    # Check Cache
    cached_pdf = PDFService.get_cached_report('balance_general', params_hash)
    if cached_pdf:
        return send_file(cached_pdf, as_attachment=True, download_name=f'Balance_General_{datetime.now().date()}.pdf', mimetype='application/pdf')

    # Get Data
    data = FinancialService.get_balance_general(start_date, end_date)
    
    # Execute queries for PDF (Lists, not query objects)
    expenses_list = data['q_expenses_list'].order_by(AdministrativeExpense.fecha.desc()).all()
    recent_diagnoses = data['q_recent_diag'].order_by(PaymentDiagnosis.fecha_pago.desc()).limit(20).all()
    recent_installments = data['q_recent_inst'].order_by(ContractInstallment.fecha_vencimiento.desc()).limit(20).all()

    # Context for PDF
    context = {
        'total_ingresos': data['total_ingresos'],
        'total_gastos': data['total_gastos'],
        'costo_negocio': data['costo_negocio'],
        'utilidad_neta': data['utilidad_neta'],
        'expenses': expenses_list,
        'recent_diagnoses': recent_diagnoses,
        'recent_installments': recent_installments,
        'start_date': start_date,
        'end_date': end_date,
        'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M')
    }

    try:
        pdf_buffer = PDFService.generate_pdf('balance_pdf.html', context)
        # Save to cache
        PDFService.save_pdf_to_cache('balance_general', params_hash, pdf_buffer)
        
        pdf_buffer.seek(0)
        return send_file(pdf_buffer, as_attachment=True, download_name=f'Balance_General_{datetime.now().date()}.pdf', mimetype='application/pdf')
    except Exception as e:
        flash(f"Error al generar el reporte: {str(e)}", "danger")
        return redirect(url_for('financial.balance_general'))
