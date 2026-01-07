from models import db, Document
from werkzeug.utils import secure_filename
import os
from flask import current_app

class DocumentService:
    @staticmethod
    def upload_file(file, client_id, user_id, visible_analyst=False, visible_client=False):
        """
        Handles file upload, saving to disk and creating a DB record.
        """
        if not file or file.filename == '':
            raise ValueError("No file selected")
            
        filename = secure_filename(file.filename)
        # Prefix with client_id to associate
        filename = f"client_{client_id}_{filename}"
        
        upload_folder = current_app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            
        file.save(os.path.join(upload_folder, filename))
        
        new_doc = Document(
            filename=filename,
            client_id=client_id,
            uploaded_by_id=user_id,
            visible_para_analista=visible_analyst,
            visible_para_cliente=visible_client
        )
        db.session.add(new_doc)
        db.session.commit()
        
        return new_doc

    @staticmethod
    def toggle_visibility(doc_id, role_type):
        """
        Toggles visibility for a document based on role type ('analyst' or 'client').
        """
        doc = Document.query.get_or_404(doc_id)
        
        if role_type == 'analyst':
            doc.visible_para_analista = not doc.visible_para_analista
            result = doc.visible_para_analista
        elif role_type == 'client':
            doc.visible_para_cliente = not doc.visible_para_cliente
            result = doc.visible_para_cliente
        else:
            raise ValueError("Invalid role type")
            
        db.session.commit()
        return result

    @staticmethod
    def get_client_documents(client_id, user_role=None):
        """
        Retrieves documents for a client, optionally filtering by visibility for specific roles.
        This replaces the os.listdir usage.
        """
        query = Document.query.filter_by(client_id=client_id)
        
        if user_role == 'Analista' or user_role == 'Aliado':
            query = query.filter_by(visible_para_analista=True)
        elif user_role == 'Cliente':
            query = query.filter_by(visible_para_cliente=True)
            
        return query.order_by(Document.created_at.desc()).all()
