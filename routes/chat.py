from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, CaseMessage, Client, User
from datetime import datetime

chat_bp = Blueprint('chat', __name__)

from utils.time_utils import get_colombia_now

@chat_bp.route('/send_message/<int:client_id>', methods=['POST'])
@login_required
def send_message(client_id):
    client = Client.query.get_or_404(client_id)
    content = request.form.get('content')
    
    if not content:
        flash('El mensaje no puede estar vacío.', 'warning')
        return redirect(request.referrer)

    MAX_MSG_LENGTH = 5000
    if len(content) > MAX_MSG_LENGTH:
        flash(f'El mensaje es demasiado largo. Máximo {MAX_MSG_LENGTH} caracteres.', 'warning')
        return redirect(request.referrer)

    # Determine validation permissions
    # Client can only send to their own case
    if current_user.rol == 'Cliente':
        if not client.login_user_id or client.login_user_id != current_user.id:
             print(f"Chat Blocked: User {current_user.id} tried to msg Client {client.id} but linking is {client.login_user_id}")
             flash('No estás autorizado para enviar mensajes a este caso. Contacta soporte.', 'danger')
             return redirect(url_for('main.index'))
    # Lawyer/Admin sends to Client
    elif current_user.rol in ['Abogado', 'Admin', 'Analista', 'Aliado']:
        pass
    else:
        flash('Rol no autorizado para chat.', 'danger')
        return redirect(url_for('main.index'))

    try:
        new_message = CaseMessage(
            content=content,
            sender_id=current_user.id,
            client_id=client.id,
            is_read_by_recipient=False,
            timestamp=get_colombia_now()
        )
        
        db.session.add(new_message)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Chat Error: {str(e)}")
        flash('Error al enviar el mensaje. Intenta nuevamente.', 'danger')
    
    return redirect(request.referrer)

@chat_bp.route('/api/messages/<int:client_id>', methods=['GET'])
@login_required
def get_messages(client_id):
    client = Client.query.get_or_404(client_id)
    
    # Validation permissions
    if current_user.rol == 'Cliente':
        if not client.login_user_id or client.login_user_id != current_user.id:
             return {'error': 'No autorizado'}, 403
    elif current_user.rol in ['Abogado', 'Admin', 'Analista', 'Aliado', 'Radicador', 'Negociador']:
        pass
    else:
        return {'error': 'Rol no autorizado'}, 403

    messages = CaseMessage.query.filter_by(client_id=client.id).order_by(CaseMessage.timestamp.asc()).all()
    
    # Mark as read (only if mark_read is not explicitly false)
    mark_read_param = request.args.get('mark_read', 'true').lower()
    
    if mark_read_param != 'false':
        unread_msgs = [m for m in messages if m.sender_id != current_user.id and not m.is_read_by_recipient]
        if unread_msgs:
            for msg in unread_msgs:
                msg.is_read_by_recipient = True
            db.session.commit()

    messages_data = [{
        'is_me': msg.sender_id == current_user.id,
        'sender_name': 'Yo' if msg.sender_id == current_user.id else msg.sender.nombre_completo,
        'content': msg.content,
        'timestamp': msg.timestamp.strftime('%d/%m %H:%M')
    } for msg in messages]

    return {'messages': messages_data}
