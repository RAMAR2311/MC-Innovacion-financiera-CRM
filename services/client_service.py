from models import db, Client, ClientStatus
from typing import Dict, Any, List
import pandas as pd

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
        nombre: str = (data.get('nombre') or '').replace('\r', '').replace('\n', '').strip()
        telefono: str = (data.get('telefono') or '').replace('\r', '').replace('\n', '').strip()
        tipo_id: str = (data.get('tipo_id') or '').replace('\r', '').replace('\n', '').strip()
        numero_id: str = (data.get('numero_id') or '').replace('\r', '').replace('\n', '').strip()
        email: str = (data.get('email') or '').replace('\r', '').replace('\n', '').strip().lower()
        ciudad: str = (data.get('ciudad') or '').replace('\r', '').replace('\n', '').strip()
        motivo_consulta: str = data.get('motivo_consulta', '').strip()

        # Manejo seguro de nulos para campo Único
        raw_contract = data.get('contract_number')
        contract_number = raw_contract.strip() if raw_contract and raw_contract.strip() else None
        
        # 3. Check for duplicates
        if numero_id and Client.query.filter_by(numero_id=numero_id).first():
            raise ValueError(f"Ya existe un cliente con el documento {numero_id}.")
            
        if contract_number and Client.query.filter_by(contract_number=contract_number).first():
             raise ValueError(f"Ya existe un cliente con el contrato {contract_number}.")

        # 4. Determine Status
        # Check specific flag from form to set status
        if data.get('incomplete'):
            estado = ClientStatus.PROSPECTO
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

    @staticmethod
    def delete_client(client_id: int) -> None:
        """
        Deletes a client and all associated records.
        """
        client = Client.query.get_or_404(client_id)
        
        try:
            db.session.delete(client)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def bulk_import(file, user_id: int) -> Dict[str, Any]:
        """
        Process an Excel file to bulk create clients.
        
        Args:
            file: The uploaded Excel file object.
            user_id: The ID of the user performing the import.
            
        Returns:
            dict: Summary of the operation {'success_count': int, 'errors': list}
        """
        try:
            df = pd.read_excel(file)
        except Exception as e:
            return {'success_count': 0, 'errors': [f"Error al leer el archivo: {str(e)}"]}

        required_columns = ['Nombre', 'Telefono']
        missing_cols = [col for col in required_columns if col not in df.columns]
        
        if missing_cols:
             return {'success_count': 0, 'errors': [f"Faltan columnas obligatorias: {', '.join(missing_cols)}"]}

        success_count = 0
        errors = []

        # Iterate over rows
        for index, row in df.iterrows():
            row_num = index + 2  # Excel row number (1-based header + 0-based index + 1 next row)
            
            # Construct data dict, handling NaN values securely
            client_data = {
                'nombre': str(row['Nombre']).strip() if pd.notna(row.get('Nombre')) else None,
                'telefono': str(row['Telefono']).strip() if pd.notna(row.get('Telefono')) else None,
                'email': str(row.get('Email', '')).strip() if pd.notna(row.get('Email')) else None,
                'cedula': str(row.get('Cedula', '')).strip() if pd.notna(row.get('Cedula')) else None, # Maps to numero_id
                'numero_id': str(row.get('Cedula', '')).strip() if pd.notna(row.get('Cedula')) else None, 
                'tipo_id': str(row.get('Tipo ID', '')).strip() if pd.notna(row.get('Tipo ID')) else None,
                'ciudad': str(row.get('Ciudad', '')).strip() if pd.notna(row.get('Ciudad')) else None,
                'contract_number': str(row.get('Contrato', '')).strip() if pd.notna(row.get('Contrato')) else None,
                'incomplete': True # Import as Prospects by default or verify logic? User said "batch creation... assigned to user".
                                   # User didn't specify status. But usually bulk imports might be prospects. 
                                   # However, create_client uses 'incomplete' flag to set PROSPECTO.
                                   # Let's assume we want them as regular NUEVO unless specified.
                                   # Actually, let's look at the request: "importar múltiples clientes... manteniendo las validaciones".
                                   # If I don't send 'incomplete', they become NUEVO. 
                                   # Maybe safer to set them as PROSPECTO if data is minimal?
                                   # But 'create_client' handles validation. If name/tel is present, it works.
                                   # Let's stick to default behavior (NUEVO) unless user asked otherwise.
                                   # Wait, the user prompt says: "reuse create_client". create_client sets NUEVO by default.
            }
            
            # Map friendly Excel headers to internal keys if needed. 
            # I mapped 'Cedula' -> 'numero_id'. 
            
            try:
                ClientService.create_client(client_data, user_id)
                success_count += 1
            except ValueError as ve:
                errors.append(f"Fila {row_num}: {str(ve)}")
            except Exception as e:
                errors.append(f"Fila {row_num}: Error inesperado - {str(e)}")
        
        return {'success_count': success_count, 'errors': errors}
