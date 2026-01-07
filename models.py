from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_completo = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(120), unique=True, nullable=False)
    rol = db.Column(db.String(20), nullable=False)  # 'Admin', 'Analista', 'Abogado', 'Aliado'
    password = db.Column(db.String(200)) # Added password for auth
    is_active = db.Column(db.Boolean, default=True) # Added for portal revocation


    payments = db.relationship('AllyPayment', backref='ally', lazy=True)

class ClientStatus:
    NUEVO = 'Nuevo'
    INFORMACION_INCOMPLETA = 'Informacion_Incompleta'
    PENDIENTE_ANALISIS = 'Pendiente_Analisis'
    CON_CONTRATO = 'Con_Contrato'
    CON_ANALISIS = 'Con_Analisis'
    RADICADO = 'Radicado'
    FINALIZADO = 'Finalizado'
    SUSPENDIDO_PAGO = 'Suspendido_Pago'
    FINALIZADO_EXITOSO = 'Finalizado_Exitoso'
    CERRADO_PAGO = 'Cerrado_Pago'
    FINALIZADO_PROCESO_CREDITO = 'Finalizado_Proceso_Credito'

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    tipo_id = db.Column(db.String(20))
    numero_id = db.Column(db.String(20))
    contract_number = db.Column(db.String(50), nullable=True, unique=True)
    telefono = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    ciudad = db.Column(db.String(50))
    motivo_consulta = db.Column(db.Text)
    estado = db.Column(db.String(50), default=ClientStatus.NUEVO) # Use keys from ClientStatus
    analista_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    abogado_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    conclusion_analisis = db.Column(db.Text) # New field for analysis conclusion
    last_status_update = db.Column(db.DateTime, default=datetime.utcnow) # New field for last status update
    login_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Link to User

    analista = db.relationship('User', foreign_keys=[analista_id], backref='clientes_registrados')
    login_user = db.relationship('User', foreign_keys=[login_user_id], backref='client_profile')

class FinancialObligation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    entidad = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(50), nullable=False) # 'Al día', 'Reportado', 'Reporte negativo de tiempo'
    valor = db.Column(db.Float, nullable=False)
    estado_legal = db.Column(db.String(100), default='Sin Iniciar') # 'Sin Iniciar', 'Derecho de aclaración', 'Refutación de pruebas', 'Derecho de petición', 'Fallo al derecho', 'Refutación a ese fallo', 'Solicitud de reposición', 'Queja superintendencia', 'Queja defensoría', 'Tutelas fallo', 'Tutela', 'Demanda juzgado', 'Demanda a la SIC', 'Negociación en curso', 'Negociación entregada', 'Negociación incumplida por el cliente', 'Finalizado'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    client = db.relationship('Client', backref=db.backref('financial_obligations', cascade='all, delete-orphan'))

class Interaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    fecha_hora_cita = db.Column(db.DateTime)
    tipo = db.Column(db.String(50)) # 'Asesoría Inicial', 'Explicación Reporte'

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    tipo_venta = db.Column(db.String(50)) # 'Analisis', 'Contrato'
    monto = db.Column(db.Float)
    fecha_venta = db.Column(db.DateTime, default=datetime.utcnow)
    comision = db.Column(db.Float)
    numero_cuotas = db.Column(db.Integer)
    observaciones = db.Column(db.Text)

class Installment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    numero_cuota = db.Column(db.String(20)) # ej: 1 de 5
    fecha_pago = db.Column(db.Date)
    monto_cuota = db.Column(db.Float)
    estado = db.Column(db.String(20), default='Pendiente') # 'Pendiente', 'Pagado'

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    visible_para_analista = db.Column(db.Boolean, default=False)
    visible_para_cliente = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    uploaded_by = db.relationship('User', backref='documents')
    client = db.relationship('Client', backref=db.backref('documents', cascade='all, delete-orphan'))

class PaymentDiagnosis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False, unique=True)
    valor = db.Column(db.Float)
    fecha_pago = db.Column(db.Date)
    metodo_pago = db.Column(db.String(50)) # 'Nequi', 'Daviplata', 'Bancolombia', 'Link de pago', 'Efectivo'
    verificado = db.Column(db.Boolean, default=False)

    client = db.relationship('Client', backref=db.backref('payment_diagnosis', uselist=False, cascade='all, delete-orphan'))

class PaymentContract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False, unique=True)
    valor_total = db.Column(db.Float)
    numero_cuotas = db.Column(db.Integer)

    client = db.relationship('Client', backref=db.backref('payment_contract', uselist=False, cascade='all, delete-orphan'))

class ContractInstallment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payment_contract_id = db.Column(db.Integer, db.ForeignKey('payment_contract.id'), nullable=False)
    numero_cuota = db.Column(db.Integer, nullable=False)
    concepto = db.Column(db.String(100)) # New field for description
    valor = db.Column(db.Float)
    fecha_vencimiento = db.Column(db.Date)
    metodo_pago = db.Column(db.String(50))
    estado = db.Column(db.String(50), default='Pendiente') # 'Pendiente', 'Pagada', 'En Mora'

    payment_contract = db.relationship('PaymentContract', backref='installments')

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    client = db.relationship('Client', backref=db.backref('messages', cascade='all, delete-orphan'))
    sender = db.relationship('User', backref='sent_messages')

class AdministrativeExpense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(255), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.Date, default=datetime.utcnow)

class AllyPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    observation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ally_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class CaseMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    is_read_by_recipient = db.Column(db.Boolean, default=False)

    sender = db.relationship('User', backref='sent_case_messages')
    client = db.relationship('Client', backref=db.backref('case_messages', cascade='all, delete-orphan'))

class ClientNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)

    author = db.relationship('User', backref='notes_authored')
    client = db.relationship('Client', backref=db.backref('notes', cascade='all, delete-orphan'))
