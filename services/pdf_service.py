import os
from xhtml2pdf import pisa
from io import BytesIO
from datetime import datetime
from typing import Dict, Any
from flask import render_template

class PDFService:
    @staticmethod
    def generate_pdf(template_name: str, context: Dict[str, Any]) -> BytesIO:
        """
        Generates a PDF buffer from a template and context.
        """
        html = render_template(template_name, **context)
        buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=buffer)
        
        if pisa_status.err:
            raise Exception(f"Error generating PDF: {pisa_status.err}")
        
        buffer.seek(0)
        return buffer

    @staticmethod
    def get_cached_report(report_name: str, params_hash: str) -> str:
        """
        Checks if a cached version of the report exists for the given params.
        """
        cache_dir = os.path.join('uploads', 'reports')
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)
        
        filename = f"{report_name}_{params_hash}.pdf"
        file_path = os.path.join(cache_dir, filename)
        
        if os.path.exists(file_path):
            return file_path
        return None

    @staticmethod
    def save_pdf_to_cache(report_name: str, params_hash: str, buffer: BytesIO) -> str:
        """
        Saves a PDF buffer to the cache directory.
        """
        cache_dir = os.path.join('uploads', 'reports')
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)
            
        filename = f"{report_name}_{params_hash}.pdf"
        file_path = os.path.join(cache_dir, filename)
        
        with open(file_path, 'wb') as f:
            f.write(buffer.getvalue())
            
        return file_path
