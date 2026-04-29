from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from flask_login import current_user, login_required
from services.financial_service import FinancialService
from services.pdf_service import PDFService
from models import PaymentDiagnosis, ContractInstallment, AdministrativeExpense, Expense, db
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
    funnel_stats = FinancialService.get_funnel_stats(start_date, end_date)

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
                           income_diagnosis=data.get('income_diagnosis', 0),
                           income_installments=data.get('income_installments', 0),
                           total_gross_income=data.get('total_gross_income', 0),
                           funnel_stats=funnel_stats,
                           recent_diagnoses=recent_diagnoses,
                           recent_installments=recent_installments,
                           current_filter=estado_filter,
                           start_date=start_date,
                           end_date=end_date)


@financial_bp.route('/balance_general', methods=['GET'])
@login_required
@role_required(['Admin', 'Abogado'])
def balance_general():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Get Data
    data = FinancialService.get_balance_general(start_date, end_date)

    return render_template('balance_general.html',
                           total_ingresos=data.get('total_ingresos', 0),
                           costo_negocio=data.get('costo_negocio', 0),
                           utilidad_neta=data.get('utilidad_neta', 0),
                           costos_totales=data['costos_totales'],
                           gastos_administrativos=data['gastos_administrativos'],
                           ventas_totales=data['ventas_totales'],
                           impuestos_clientes=data['impuestos_clientes'],
                           start_date=data['start_date_used'],
                           end_date=data['end_date_used'])


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
    expenses_list = [] # Expenses are now separated

    recent_diagnoses = data['q_recent_diag'].order_by(PaymentDiagnosis.fecha_pago.desc()).limit(20).all()
    recent_installments = data['q_recent_inst'].order_by(ContractInstallment.fecha_vencimiento.desc()).limit(20).all()

    # Context for PDF
    context = {
        'total_ingresos': data.get('total_ingresos', 0),
        'costo_negocio': data.get('costo_negocio', 0),
        'utilidad_neta': data.get('utilidad_neta', 0),
        'costos_totales': data['costos_totales'],
        'ventas_totales': data['ventas_totales'],
        'ventas_diagnosticos': data.get('ventas_diagnosticos', 0),
        'ventas_contratos': data.get('ventas_contratos', 0),
        'costos_directos': data.get('costos_directos', 0),
        'costos_indirectos': data.get('costos_indirectos', 0),
        'gastos_administrativos': data['gastos_administrativos'],
        'utilidad_bruta': data['ventas_totales'] - (data['costos_totales'] + data['gastos_administrativos']),
        'total_iva': data.get('total_iva', 0),
        'total_retefuente': data.get('total_retefuente', 0),
        'total_ica': data.get('total_ica', 0),
        'impuestos_clientes': data['impuestos_clientes'],
        'utilidad_neta': data['ventas_totales'] - (data['costos_totales'] + data['gastos_administrativos']) - data['impuestos_clientes'],
        'expenses': expenses_list,
        'recent_diagnoses': recent_diagnoses,
        'recent_installments': recent_installments,
        'start_date': data['start_date_used'],
        'end_date': data['end_date_used'],
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

@financial_bp.route('/gastos', methods=['GET', 'POST'])
@login_required
@role_required(['Admin', 'Abogado'])
def panel_gastos():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if request.method == 'POST':
        tipo = request.form.get('tipo')
        descripcion = request.form.get('descripcion')
        valor_base = request.form.get('valor_base')
        valor_impuesto = request.form.get('valor_impuesto', 0.0)
        
        if not (tipo and descripcion and valor_base):
            flash('Por favor complete todos los campos obligatorios del gasto.', 'warning')
        else:
            try:
                # Determinar fecha o usar actual
                expense_date = datetime.now()
                fecha_input = request.form.get('fecha')
                if fecha_input:
                    try:
                        expense_date = datetime.strptime(fecha_input, '%Y-%m-%d')
                    except ValueError:
                        pass
                
                new_expense = Expense(
                    tipo=tipo,
                    descripcion=descripcion,
                    valor_base=float(valor_base),
                    valor_impuesto=float(valor_impuesto),
                    fecha=expense_date,
                    usuario_id=current_user.id
                )
                db.session.add(new_expense)
                db.session.commit()
                flash('Gasto registrado exitosamente.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error al registrar gasto: {str(e)}', 'danger')
        
        return redirect(url_for('financial.panel_gastos', start_date=start_date, end_date=end_date))

    # Calculate summary
    summary = FinancialService.get_expense_summary(start_date, end_date)
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    expenses = summary['q_expenses_list'].order_by(Expense.fecha.desc()).paginate(page=page, per_page=20)

    return render_template('gastos.html', 
                           summary=summary,
                           expenses=expenses,
                           start_date=start_date,
                           end_date=end_date)

