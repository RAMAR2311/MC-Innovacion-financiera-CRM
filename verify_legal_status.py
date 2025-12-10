from app import app, db
from models import User, Client, FinancialObligation

def verify_legal_status():
    with app.app_context():
        # Setup
        # Create temp lawyer
        temp_lawyer_email = 'temp_lawyer_verify@test.com'
        temp_lawyer = User.query.filter_by(email=temp_lawyer_email).first()
        if not temp_lawyer:
            temp_lawyer = User(nombre_completo='Temp Lawyer', email=temp_lawyer_email, rol='Abogado', password='password')
            db.session.add(temp_lawyer)
            db.session.commit()
        
        lawyer_email = temp_lawyer.email
        lawyer_password = 'password'

        client = Client(nombre='Legal Status Test', telefono='123', estado='Pendiente_Analisis')
        db.session.add(client)
        db.session.commit()
        client_id = client.id

        obligation = FinancialObligation(
            client_id=client.id,
            entidad='Test Bank',
            estado='Reportado',
            valor=100000
        )
        db.session.add(obligation)
        db.session.commit()
        obligation_id = obligation.id

    # Test Route
    with app.test_client() as client_web:
        # Login
        client_web.post('/login', data={'email': lawyer_email, 'password': lawyer_password}, follow_redirects=True)
        
        # Update Status
        response = client_web.post(f'/obligation/{obligation_id}/update_legal_status', data={'estado_legal': 'En Tutela'}, follow_redirects=True)
        
        if response.status_code == 200:
            print("Request successful.")
        else:
            print(f"Request failed: {response.status_code}")

    # Verify DB
    with app.app_context():
        obl = FinancialObligation.query.get(obligation_id)
        if obl:
            if obl.estado_legal == 'En Tutela':
                print("SUCCESS: Legal status updated to 'En Tutela'.")
            else:
                print(f"FAILURE: Legal status is '{obl.estado_legal}'.")
            
            # Cleanup
            db.session.delete(obl)
            db.session.delete(Client.query.get(client_id))
            db.session.delete(User.query.filter_by(email=temp_lawyer_email).first())
            db.session.commit()
        else:
             print("FAILURE: Obligation not found.")

if __name__ == '__main__':
    verify_legal_status()
