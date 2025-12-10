from app import app, db, User

with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='admin@mc.com').first():
        admin = User(nombre_completo='Admin', email='admin@mc.com', rol='Admin', password='admin')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created.")
    print("Database initialized.")
