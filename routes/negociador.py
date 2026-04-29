from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Client, User, FinancialObligation, Negotiation
from utils.decorators import role_required
from utils.time_utils import get_colombia_now
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

negociador_bp = Blueprint('negociador', __name__)

@negociador_bp.route('/negociador')
@login_required
@role_required(['Negociador', 'Admin'])
def dashboard():
    """Dashboard del negociador: muestra solo las obligaciones asignadas para negociación."""
    nombre = request.args.get('nombre')
    estado = request.args.get('estado')

    query = Negotiation.query.options(
        joinedload(Negotiation.obligation).joinedload(FinancialObligation.client),
        joinedload(Negotiation.negociador)
    )

    if current_user.rol == 'Negociador':
        query = query.filter(Negotiation.negociador_id == current_user.id)

    if nombre:
        search_term = f'%{nombre}%'
        query = query.join(Negotiation.obligation).join(FinancialObligation.client).filter(
            or_(
                Client.nombre.ilike(search_term),
                Client.numero_id.ilike(search_term)
            )
        )
    
    if estado:
        query = query.filter(Negotiation.estado == estado)
    
    page = request.args.get('page', 1, type=int)
    negotiations = query.order_by(Negotiation.created_at.desc()).paginate(page=page, per_page=20)

    return render_template('negociador/dashboard.html', negotiations=negotiations)


@negociador_bp.route('/negociador/negotiation/<int:negotiation_id>', methods=['GET'])
@login_required
@role_required(['Negociador', 'Admin'])
def negotiation_detail(negotiation_id):
    """Vista de detalle de una negociación específica."""
    negotiation = Negotiation.query.options(
        joinedload(Negotiation.obligation).joinedload(FinancialObligation.client),
    ).get_or_404(negotiation_id)

    if current_user.rol == 'Negociador' and negotiation.negociador_id != current_user.id:
        flash('No tienes permiso para ver esta negociación.', 'danger')
        return redirect(url_for('negociador.dashboard'))

    return render_template('negociador/detail.html', negotiation=negotiation)


@negociador_bp.route('/negociador/negotiation/<int:negotiation_id>/update', methods=['POST'])
@login_required
@role_required(['Negociador', 'Admin'])
def update_negotiation(negotiation_id):
    """Actualizar los campos de gestión de una negociación."""
    negotiation = Negotiation.query.get_or_404(negotiation_id)

    if current_user.rol == 'Negociador' and negotiation.negociador_id != current_user.id:
        flash('No tienes permiso para editar esta negociación.', 'danger')
        return redirect(url_for('negociador.dashboard'))

    negotiation.valor_negociado = request.form.get('valor_negociado', type=float)
    negotiation.condiciones = request.form.get('condiciones', '').strip()
    negotiation.observaciones = request.form.get('observaciones', '').strip()
    new_estado = request.form.get('estado')
    if new_estado:
        negotiation.estado = new_estado
    
    negotiation.updated_at = get_colombia_now()
    db.session.commit()
    flash('Negociación actualizada exitosamente.', 'success')
    return redirect(url_for('negociador.negotiation_detail', negotiation_id=negotiation_id))


@negociador_bp.route('/obligation/<int:obligation_id>/send_to_negotiation', methods=['POST'])
@login_required
@role_required(['Abogado', 'Admin', 'Analista', 'Aliado', 'Radicador'])
def send_to_negotiation(obligation_id):
    """Enviar una obligación financiera a negociación, creando el registro de Negotiation."""
    obligation = FinancialObligation.query.get_or_404(obligation_id)

    # Verificar si ya existe una negociación activa para esta obligación
    existing = Negotiation.query.filter_by(obligation_id=obligation_id).filter(
        Negotiation.estado.notin_(['Finalizada', 'Cancelada'])
    ).first()
    
    if existing:
        flash('Esta obligación ya tiene una negociación activa.', 'warning')
        return redirect(url_for('main.client_detail', client_id=obligation.client_id))
    
    # Buscar un negociador disponible
    negociador_id = request.form.get('negociador_id')
    if negociador_id:
        negociador = User.query.get(negociador_id)
    else:
        negociador = User.query.filter_by(rol='Negociador').first()
    
    if not negociador:
        flash('No hay negociadores disponibles para asignar.', 'warning')
        return redirect(url_for('main.client_detail', client_id=obligation.client_id))
    
    new_negotiation = Negotiation(
        obligation_id=obligation_id,
        negociador_id=negociador.id,
        estado='Pendiente',
        created_at=get_colombia_now()
    )
    db.session.add(new_negotiation)
    
    # Actualizar estado legal de la obligación
    obligation.estado_legal = 'Negociación en curso'
    
    db.session.commit()

    flash(f'Obligación enviada a negociación con {negociador.nombre_completo}.', 'success')
    return redirect(url_for('main.client_detail', client_id=obligation.client_id))
