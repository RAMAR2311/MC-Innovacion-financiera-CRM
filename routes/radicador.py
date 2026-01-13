from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Client, User, ClientStatus
from utils.decorators import role_required
from sqlalchemy import or_

radicador_bp = Blueprint('radicador', __name__)

@radicador_bp.route('/radicador')
@login_required
@role_required(['Radicador', 'Admin'])
def radicador_dashboard():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '')
    status_filter = request.args.get('estado', '')
    date_filter = request.args.get('fecha', '')

    query = Client.query

    # Si es Radicador, ver solo sus asignados
    if current_user.rol == 'Radicador':
        query = query.filter_by(radicador_id=current_user.id)

    # Filtros de búsqueda logic similar a otros paneles
    if search_query:
        search = f"%{search_query}%"
        query = query.filter(
            or_(
                Client.nombre.ilike(search),
                Client.numero_id.ilike(search),
                Client.email.ilike(search)
            )
        )
    
    if status_filter:
        query = query.filter(Client.estado == status_filter)

    if date_filter:
        try:
            query = query.filter(db.func.date(Client.created_at) == date_filter)
        except:
            pass

    # Ordenar por fecha de creación descendente por defecto
    query = query.order_by(Client.created_at.desc())

    clients = query.paginate(page=page, per_page=20)
    
    return render_template('radicador/dashboard.html', clients=clients)
