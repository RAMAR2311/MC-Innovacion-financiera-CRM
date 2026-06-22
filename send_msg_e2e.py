import time
time.sleep(10)
from app import app
from models import db, User, Client, CaseMessage
from datetime import datetime

with app.app_context():
    client = Client.query.first()
    if client:
        msg = CaseMessage()
        msg.content = 'MENSAJE E2E PARA VIDEO'
        msg.sender_id = 23
        msg.client_id = client.id
        msg.is_read_by_recipient = False
        msg.timestamp = datetime.utcnow()
        db.session.add(msg)
        db.session.commit()
        print('Mensaje E2E enviado')
