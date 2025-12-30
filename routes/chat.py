from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, CaseMessage, Client, User
from datetime import datetime

chat_bp = Blueprint('chat', __name__)

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
            is_read_by_recipient=False
        )
        
        db.session.add(new_message)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Chat Error: {str(e)}")
        flash('Error al enviar el mensaje. Intenta nuevamente.', 'danger')
    
    return redirect(request.referrer)
