import os

files = {
    "app/repositories/medical_document_repository.py": """from app.repositories.base_repository import BaseRepository

class MedicalDocumentRepository(BaseRepository):
    TABLE = "MedicalDocuments"
    
    def get_patient_documents(self, patient_id):
        return self.query_index(
            self.TABLE,
            "patient-index",
            "PatientID = :pid",
            {":pid": patient_id}
        )
""",
    "app/services/storage_service.py": """import boto3
import os
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.s3 = boto3.client('s3', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
        self.bucket = os.environ.get('S3_BUCKET_NAME', 'medtrack-documents-local')

    def upload_file(self, file_obj, object_name, content_type=None):
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        try:
            self.s3.upload_fileobj(file_obj, self.bucket, object_name, ExtraArgs=extra_args)
            return True
        except ClientError as e:
            logger.error(e)
            return False

    def get_presigned_url(self, object_name, expiration=3600):
        try:
            response = self.s3.generate_presigned_url('get_object',
                                                    Params={'Bucket': self.bucket, 'Key': object_name},
                                                    ExpiresIn=expiration)
        except ClientError as e:
            logger.error(e)
            return None
        return response
""",
    "app/services/pdf_service.py": """import io
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
        for line in medicines.split('\\n'):
            text.textLine(line)
        c.drawText(text)
        
        c.save()
        buffer.seek(0)
        
        object_name = f"prescriptions/{rx_id}.pdf"
        self.storage.upload_file(buffer, object_name, content_type='application/pdf')
        return object_name
""",
    "app/lambdas/reminder_lambda.py": """import os
import boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
TABLE_NAME = os.environ.get('APPOINTMENT_TABLE', 'MedTrack-Appointments')
TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')

def lambda_handler(event, context):
    table = dynamodb.Table(TABLE_NAME)
    tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')
    response = table.scan(
        FilterExpression="begins_with(ScheduledAt, :t) AND #st = :s",
        ExpressionAttributeValues={":t": tomorrow, ":s": "Confirmed"},
        ExpressionAttributeNames={"#st": "Status"}
    )
    
    count = 0
    for item in response.get('Items', []):
        patient_id = item['PatientID']
        msg = f"Reminder: You have a MedTrack appointment tomorrow at {item['ScheduledAt']}"
        if TOPIC_ARN:
            try:
                sns.publish(TopicArn=TOPIC_ARN, Message=msg)
                count += 1
            except Exception as e:
                print(f"Failed to send SMS to patient {patient_id}: {e}")
                
    return {"statusCode": 200, "body": f"Sent {count} reminders."}
""",
    "scripts/setup_eventbridge.py": """import boto3
import json

def setup_eventbridge(lambda_arn):
    events = boto3.client('events')
    
    # Create rule to trigger daily at 8:00 AM UTC
    rule_response = events.put_rule(
        Name='MedTrackDailyReminders',
        ScheduleExpression='cron(0 8 * * ? *)',
        State='ENABLED',
        Description='Triggers daily appointment reminders'
    )
    
    # Add lambda as target
    events.put_targets(
        Rule='MedTrackDailyReminders',
        Targets=[
            {
                'Id': 'ReminderLambdaTarget',
                'Arn': lambda_arn
            }
        ]
    )
    print("EventBridge Rule established successfully.")

if __name__ == '__main__':
    # usage: python setup_eventbridge.py
    # NOTE: requires an actual Lambda ARN to be functional in a real AWS env.
    print("Setup script loaded. Pass your deployed Lambda ARN to run.")
""",
    "tests/test_aws_services.py": """import pytest
import boto3
import io
from moto import mock_aws
from app.services.storage_service import StorageService

@pytest.fixture
def s3_setup(aws_credentials):
    with mock_aws():
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='medtrack-documents-local')
        yield

def test_upload_and_presign(s3_setup):
    svc = StorageService()
    file_obj = io.BytesIO(b"dummy pdf content")
    success = svc.upload_file(file_obj, "test.pdf")
    assert success is True
    
    url = svc.get_presigned_url("test.pdf")
    assert url is not None
    assert "AWSAccessKeyId" in url
"""
}

for path, content in files.items():
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

# Patching patient_forms.py
with open('app/forms/patient_forms.py', 'r') as f:
    form_content = f.read()
if "DocumentUploadForm" not in form_content:
    form_content += """
from flask_wtf.file import FileField, FileAllowed, FileRequired
class DocumentUploadForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    document = FileField('Document', validators=[FileRequired(), FileAllowed(['pdf', 'png', 'jpg'], 'PDF or Images only!')])
    submit = SubmitField('Upload')
"""
    with open('app/forms/patient_forms.py', 'w') as f:
        f.write(form_content)

# Patching patient_service.py to support documents and prescriptions
with open('app/services/patient_service.py', 'r') as f:
    svc_content = f.read()

if "MedicalDocumentRepository" not in svc_content:
    svc_content = svc_content.replace(
        "from app.repositories.vitals_repository import VitalsRepository",
        "from app.repositories.vitals_repository import VitalsRepository\nfrom app.repositories.medical_document_repository import MedicalDocumentRepository\nfrom app.repositories.prescription_repository import PrescriptionRepository\nfrom app.services.storage_service import StorageService"
    )
    svc_content = svc_content.replace(
        "self.vitals_repo = VitalsRepository()",
        "self.vitals_repo = VitalsRepository()\n        self.doc_upload_repo = MedicalDocumentRepository()\n        self.rx_repo = PrescriptionRepository()\n        self.storage = StorageService()"
    )
    
    methods = """
    def get_prescriptions(self, patient_id):
        return self.rx_repo.query_index(self.rx_repo.TABLE, 'patient-index', 'PatientID = :pid', {':pid': patient_id})

    def get_prescription_by_id(self, rx_id):
        return self.rx_repo.get_item(self.rx_repo.TABLE, {'PrescriptionID': rx_id})

    def get_documents(self, patient_id):
        return self.doc_upload_repo.get_patient_documents(patient_id)

    def upload_document(self, patient_id, title, file_obj, filename):
        doc_id = str(uuid.uuid4())
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'bin'
        s3_key = f"documents/{patient_id}/{doc_id}.{ext}"
        
        # Upload to S3
        self.storage.upload_file(file_obj, s3_key)
        
        # Save metadata
        item = {
            "DocumentID": doc_id,
            "PatientID": patient_id,
            "Title": title,
            "S3Key": s3_key,
            "UploadedAt": get_utc_now(),
            "IsDeleted": False
        }
        self.doc_upload_repo.put_item(self.doc_upload_repo.TABLE, item)
        
    def get_document_url(self, s3_key):
        return self.storage.get_presigned_url(s3_key)
"""
    svc_content += methods
    with open('app/services/patient_service.py', 'w') as f:
        f.write(svc_content)


# Replace documents.html completely
documents_html = """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Medical Documents</h1>
<div class="row">
    <div class="col-md-4">
        <form method="POST" enctype="multipart/form-data" class="card p-3 shadow-sm border-0">
            {{ form.hidden_tag() }}
            {{ form.title.label }} {{ form.title(class="form-control mb-2") }}
            {{ form.document.label }} {{ form.document(class="form-control mb-3") }}
            {{ form.submit(class="btn btn-primary") }}
        </form>
    </div>
    <div class="col-md-8">
        <table class="table table-striped">
            <tr><th>Title</th><th>Uploaded At</th><th>Action</th></tr>
            {% for doc in documents %}
            <tr>
                <td>{{ doc.Title }}</td><td>{{ doc.UploadedAt }}</td>
                <td><a href="{{ url_for('patient.download_document', s3_key=doc.S3Key) }}" target="_blank" class="btn btn-sm btn-info">View / Download</a></td>
            </tr>
            {% else %}<tr><td colspan="3">No documents uploaded.</td></tr>{% endfor %}
        </table>
    </div>
</div>
<h2 class="mt-5 mb-4">Prescriptions</h2>
<table class="table table-striped">
    <tr><th>Date</th><th>Medicines</th><th>Action</th></tr>
    {% for rx in prescriptions %}
    <tr>
        <td>{{ rx.CreatedAt }}</td><td>{{ rx.Medicines[:30] }}...</td>
        <td><a href="{{ url_for('patient.download_prescription', rx_id=rx.PrescriptionID) }}" class="btn btn-sm btn-success">Generate PDF</a></td>
    </tr>
    {% else %}<tr><td colspan="3">No prescriptions found.</td></tr>{% endfor %}
</table>
{% endblock %}"""
with open('app/templates/patient/documents.html', 'w', encoding='utf-8') as f:
    f.write(documents_html)

# Patch app/blueprints/patient.py
with open('app/blueprints/patient.py', 'r') as f:
    bp_content = f.read()

if "DocumentUploadForm" not in bp_content:
    bp_content = bp_content.replace(
        "from app.forms.patient_forms import ProfileForm, DoctorSearchForm, BookingForm, VitalsForm",
        "from app.forms.patient_forms import ProfileForm, DoctorSearchForm, BookingForm, VitalsForm, DocumentUploadForm"
    )
    doc_route = """@patient_bp.route('/documents', methods=['GET', 'POST'])
def documents():
    from app.services.patient_service import PatientService
    svc = PatientService()
    form = DocumentUploadForm()
    
    if form.validate_on_submit():
        f = form.document.data
        svc.upload_document(session['user_id'], form.title.data, f, f.filename)
        flash('Document uploaded to secure S3 storage.', 'success')
        return redirect(url_for('patient.documents'))
        
    docs = svc.get_documents(session['user_id'])
    rxs = svc.get_prescriptions(session['user_id'])
    return render_template('patient/documents.html', form=form, documents=docs, prescriptions=rxs)

@patient_bp.route('/documents/download')
def download_document():
    from app.services.patient_service import PatientService
    svc = PatientService()
    s3_key = request.args.get('s3_key')
    url = svc.get_document_url(s3_key)
    if url:
        return redirect(url)
    flash("Could not generate secure link.", "danger")
    return redirect(url_for('patient.documents'))

@patient_bp.route('/prescriptions/<rx_id>/download')
def download_prescription(rx_id):
    from app.services.patient_service import PatientService
    from app.services.pdf_service import PdfService
    svc = PatientService()
    pdf_svc = PdfService()
    
    rx = svc.get_prescription_by_id(rx_id)
    if not rx or rx['PatientID'] != session['user_id']:
        return "Unauthorized", 403
        
    # Generate PDF, upload to S3, get url
    s3_key = pdf_svc.generate_and_upload_prescription(rx_id, "Doctor", "Patient", rx.get('Medicines', ''), rx.get('CreatedAt', ''))
    url = svc.get_document_url(s3_key)
    return redirect(url)
"""
    bp_content = bp_content.replace(
        "@patient_bp.route('/documents', methods=['GET', 'POST'])\ndef documents(): return render_template('patient/documents.html')",
        doc_route
    )
    with open('app/blueprints/patient.py', 'w') as f:
        f.write(bp_content)
