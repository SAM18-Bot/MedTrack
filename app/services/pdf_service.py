import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from app.services.storage_service import StorageService

class PdfService:
    def __init__(self):
        self.storage = StorageService()

    def generate_and_upload_prescription(self, rx_id, doctor_name, patient_name, medicines, date_str):
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, f"MedTrack - Electronic Prescription")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, 720, f"Prescription ID: {rx_id}")
        c.drawString(100, 700, f"Doctor: {doctor_name}")
        c.drawString(100, 680, f"Patient: {patient_name}")
        c.drawString(100, 660, f"Date: {date_str}")
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 620, f"Medicines prescribed:")
        
        c.setFont("Helvetica", 12)
        text = c.beginText(100, 600)
        for line in medicines.split('\n'):
            text.textLine(line)
        c.drawText(text)
        
        c.save()
        buffer.seek(0)
        
        object_name = f"prescriptions/{rx_id}.pdf"
        self.storage.upload_file(buffer, object_name, content_type='application/pdf')
        return object_name
