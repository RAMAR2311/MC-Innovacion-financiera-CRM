from flask import Blueprint, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Client, Interaction, User
from datetime import datetime, timedelta, time
from utils.time_utils import get_colombia_now
from utils.decorators import role_required

appointments_bp = Blueprint('appointments', __name__)

CONTRACT_SLOTS = [
    '08:00', '08:45', '09:30', '10:15', 
    '11:00', '11:45', '12:30', '13:15'
]

@appointments_bp.route('/api/slots/<int:client_id>')
@login_required
def get_slots(client_id):
    date_str = request.args.get('date')
    if not date_str:
        return jsonify([])
    
    try:
        requested_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify([])

    # 1. Validation: Past dates and Weekends (Fri-Sun for this logic, user said Mon-Thu)
    # Weekday: Mon=0, Thu=3. Fri=4, Sat=5, Sun=6.
    now = get_colombia_now()
    today = now.date()

    if requested_date < today:
        return jsonify([])
    
    # Allow Mon(0) to Thu(3). Disallow Fri(4), Sat(5), Sun(6)
    if requested_date.weekday() > 3:
        return jsonify([]) # No service Fri-Sun
    
    client = Client.query.get_or_404(client_id)
    lawyer_id = client.abogado_id
    
    if not lawyer_id:
        return jsonify([]) # No lawyer assigned, can't book

    # Define Slots based on Role
    # CASE A: Client -> Afternoons
    # CASE B: Staff -> Mornings
    
    if current_user.rol == 'Cliente':
        slots_to_check = ['14:00', '14:45', '15:30', '16:15', '17:00', '17:45']
        # The purpose is "Entrega de Avances"
    else:
        # Admin, Abogado, Aliado, Radicador, Analista
        slots_to_check = ['08:00', '08:45', '09:30', '10:15', '11:00', '11:45', '12:30', '13:15']

    # 2. Get existing interactions for that lawyer on that date
    start_of_day = datetime.combine(requested_date, time.min)
    end_of_day = datetime.combine(requested_date, time.max)
    
    # We check ALL interactions that are strict appointments to block slots
    existing_appts = Interaction.query.filter(
        Interaction.usuario_id == lawyer_id,
        Interaction.fecha_hora_cita >= start_of_day,
        Interaction.fecha_hora_cita <= end_of_day,
        Interaction.tipo == 'Reunión Agendada'
    ).all()
    
    occupied_times = set()
    for appt in existing_appts:
        if appt.fecha_hora_cita:
            occupied_times.add(appt.fecha_hora_cita.strftime('%H:%M'))
            
    # 3. Filter available slots
    available_slots = []
    
    # If today, filter out past times
    current_time_str = now.strftime('%H:%M')
    
    for slot in slots_to_check:
        if requested_date == today and slot <= current_time_str:
            continue
            
        if slot not in occupied_times:
            available_slots.append({'time': slot, 'label': slot})
            
    return jsonify(available_slots)

@appointments_bp.route('/book_appointment/<int:client_id>', methods=['POST'])
@login_required
def book_appointment(client_id):
    client = Client.query.get_or_404(client_id)
    
    # Permission check: Client themselves OR staff (Analyst/Admin/Ally/Lawyer)
    if current_user.rol == 'Cliente':
        if client.login_user_id != current_user.id:
            flash('No autorizado.', 'danger')
            return redirect(url_for('main.client_portal'))
    else:
        # Check broad permissions for staff
        if current_user.rol not in ['Analista', 'Abogado', 'Aliado', 'Admin', 'Radicador']:
             flash('No autorizado.', 'danger')
             return redirect(url_for('main.index'))
             
    date_str = request.form.get('date')
    time_str = request.form.get('time')
    
    if not date_str or not time_str:
        flash('Datos incompletos.', 'danger')
        return redirect(request.referrer or url_for('main.client_detail', client_id=client_id))
    
    try:
        appt_datetime = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
    except ValueError:
        flash('Formato de fecha inválido.', 'danger')
        return redirect(request.referrer)
        
    lawyer_id = client.abogado_id
    if not lawyer_id:
        flash('No hay abogado asignado para agendar.', 'danger')
        return redirect(request.referrer)
        
    # Double check availability (Race condition check)
    existing = Interaction.query.filter_by(
        usuario_id=lawyer_id,
        fecha_hora_cita=appt_datetime,
        tipo='Reunión Agendada'
    ).first()
    
    if existing:
        flash('Lo sentimos, esa hora ya fue ocupada. Por favor elige otra.', 'warning')
        return redirect(request.referrer)
        
    new_appt = Interaction(
        cliente_id=client.id,
        usuario_id=lawyer_id,
        fecha_hora_cita=appt_datetime,
        tipo='Reunión Agendada'
    )
    
    db.session.add(new_appt)
    db.session.commit()
    
    flash(f'Reunión agendada exitosamente para el {date_str} a las {time_str}.', 'success')
    
    if current_user.rol == 'Cliente':
        return redirect(url_for('main.client_portal'))
    else:
        return redirect(url_for('main.client_detail', client_id=client_id))

@appointments_bp.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    appt = Interaction.query.get_or_404(appointment_id)
    
    # Permission: Admin, Assigned Lawyer, or the Client themselves (Maybe?)
    # Requirement said "Vista del abogado" so specifically lawyer/admin control usually. 
    # But usually clients should cancel too. Let's stick to safe roles for now or owner.
    
    allow = False
    if current_user.rol == 'Admin':
        allow = True
    elif current_user.rol == 'Abogado' and appt.usuario_id == current_user.id:
        allow = True
    # Can client cancel? Usually yes. 
    elif current_user.rol == 'Cliente' and appt.cliente_id == current_user.client_profile[0].id: # Assuming relation backref exists or we check query
        # We need to be careful. The model Interaction has `cliente_id`. 
        # Client user map is `Client.login_user_id`.
        # current_user.client_profile is a list backref if one-to-many or object if one-to-one uselist=False.
        # Check models.py: `backref='client_profile'` on `login_user`.
        # `login_user` is ManyToOne so `client_profile` on User is OneToMany list.
        # User might have multiple clients? Theoretically no, but list.
        user_client = None
        if current_user.client_profile:
             user_client = current_user.client_profile[0]
        
        if user_client and user_client.id == appt.cliente_id:
            allow = True
            
    if not allow:
        flash('No autorizado para cancelar esta cita.', 'danger')
        return redirect(request.referrer)
        
    db.session.delete(appt)
    db.session.commit()
    flash('Cita cancelada correctamente.', 'success')
    
    return redirect(request.referrer)
