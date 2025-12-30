from models import db, Client, ClientStatus
from typing import Dict, Any

class ClientService:
    @staticmethod
    def create_client(data: Dict[str, Any], analyst_id: int) -> Client:
        """
        Creates a new client after validating the input data.
        
        Args:
            data (dict): Dictionary with client data (from form).
            analyst_id (int): ID of the analyst creating the client.
            
        Returns:
            Client: The created client object.
            
        Raises:
            ValueError: If validation fails.
        """
        
        # 1. Validate required fields (Basic validation)
        required_fields = ['nombre', 'telefono']
        for field in required_fields:
            if not data.get(field):
                 # 'email' is optional in original code but logical to have. 
                 # 'contract_number' and 'numero_id' are optional.
                 raise ValueError(f"El campo '{field}' es obligatorio.")

        # 2. Extract Data
        nombre: str = data.get('nombre')
        telefono: str = data.get('telefono')
        tipo_id: str = data.get('tipo_id')
        numero_id: str = data.get('numero_id')
        email: str = data.get('email')
        ciudad: str = data.get('ciudad')
        motivo_consulta: str = data.get('motivo_consulta')
        contract_number: str = data.get('contract_number')
        
        # 3. Check for duplicates
        if numero_id and Client.query.filter_by(numero_id=numero_id).first():
            raise ValueError(f"Ya existe un cliente con el documento {numero_id}.")
            
        if contract_number and Client.query.filter_by(contract_number=contract_number).first():
             raise ValueError(f"Ya existe un cliente con el contrato {contract_number}.")

        # 4. Determine Status
        # Check specific flag from form to set status
        if data.get('incomplete'):
            estado = ClientStatus.INFORMACION_INCOMPLETA
        else:
            estado = ClientStatus.NUEVO

        # 5. Create Object
        client = Client(
            nombre=nombre, 
            telefono=telefono, 
            tipo_id=tipo_id,
            numero_id=numero_id,
            contract_number=contract_number,
            email=email,
            ciudad=ciudad,
            motivo_consulta=motivo_consulta,
            estado=estado, 
            analista_id=analyst_id
        )
        
        # 6. Save to DB
        db.session.add(client)
        db.session.commit()
        
        return client
