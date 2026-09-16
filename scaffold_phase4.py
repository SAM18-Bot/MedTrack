import os

files = {
    "app/forms/support_forms.py": """from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email

class ContactUsForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    subject = StringField('Subject', validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send Message')

class TicketForm(FlaskForm):
    category = SelectField('Category', choices=[('Billing', 'Billing'), ('Technical', 'Technical'), ('Medical', 'Medical'), ('Other', 'Other')], validators=[DataRequired()])
    priority = SelectField('Priority', choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], validators=[DataRequired()])
    subject = StringField('Subject', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    submit = SubmitField('Submit Ticket')
""",
    "app/repositories/support_ticket_repository.py": """from app.repositories.base_repository import BaseRepository

class SupportTicketRepository(BaseRepository):
    TABLE = "SupportTickets"

    def get_user_tickets(self, user_id):
        return self.query_index(
            self.TABLE,
            "user-index",
            "UserID = :uid",
            {":uid": user_id}
        )
""",
    "app/services/notification_service.py": """import boto3
import os
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.sns = boto3.client('sns', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
        self.topic_arn = os.environ.get('SNS_TOPIC_ARN', None)

    def send_otp(self, phone: str, otp: str) -> bool:
        message = f"Your MedTrack OTP is: {otp}. It is valid for 10 minutes."
        if not self.topic_arn:
            logger.info(f"Simulating SMS to {phone}: {message}")
            return True
        try:
            self.sns.publish(PhoneNumber=phone, Message=message)
            return True
        except ClientError as e:
            logger.error(f"Failed to send OTP via SNS: {e}")
            return False

    def notify_admin(self, subject: str, message: str) -> bool:
        if not self.topic_arn:
            logger.info(f"Simulating Admin Alert - {subject}: {message}")
            return True
        try:
            self.sns.publish(TopicArn=self.topic_arn, Subject=subject, Message=message)
            return True
        except ClientError as e:
            logger.error(f"Failed to notify admin via SNS: {e}")
            return False
""",
    "app/services/support_service.py": """import uuid
from app.repositories.support_ticket_repository import SupportTicketRepository
from app.services.notification_service import NotificationService
from app.utils import get_utc_now

class SupportService:
    def __init__(self):
        self.ticket_repo = SupportTicketRepository()
        self.notification = NotificationService()

    def raise_ticket(self, user_id, category, priority, subject, description, is_guest=False):
        ticket_id = str(uuid.uuid4())
        ticket = {
            "TicketID": ticket_id,
            "UserID": user_id if not is_guest else "GUEST",
            "Category": category,
            "Priority": priority,
            "Subject": subject,
            "Description": description,
            "Status": "Open",
            "IsDeleted": False,
            "CreatedAt": get_utc_now(),
            "UpdatedAt": get_utc_now()
        }
        self.ticket_repo.put_item(self.ticket_repo.TABLE, ticket)
        msg = f"Priority [{priority}] - {subject}: {description[:100]}..."
        self.notification.notify_admin("New Support Ticket", msg)
        return ticket_id
""",
    "app/blueprints/public.py": """from flask import Blueprint, render_template, redirect, url_for, flash
from app.forms.support_forms import ContactUsForm
from app.services.support_service import SupportService

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index(): return render_template('public/landing.html')
@public_bp.route('/about')
def about(): return render_template('public/about.html')
@public_bp.route('/services')
def services(): return render_template('public/services.html')
@public_bp.route('/how-it-works')
def how_it_works(): return render_template('public/how_it_works.html')
@public_bp.route('/for-doctors')
def for_doctors(): return render_template('public/for_doctors.html')
@public_bp.route('/faq')
def faq(): return render_template('public/faq.html')

@public_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactUsForm()
    if form.validate_on_submit():
        svc = SupportService()
        msg = f"From: {form.name.data} ({form.email.data}) - {form.message.data}"
        svc.raise_ticket('GUEST', 'Other', 'Medium', form.subject.data, msg, is_guest=True)
        flash('Your message has been sent. We will get back to you shortly.', 'success')
        return redirect(url_for('public.contact'))
    return render_template('public/contact.html', form=form)

@public_bp.route('/legal/<page>')
def legal(page):
    valid_pages = ['terms', 'privacy', 'cookies', 'disclaimer', 'refund', 'data-protection', 'accessibility']
    if page not in valid_pages:
        return render_template('errors/404.html'), 404
    return render_template(f'public/legal_{page}.html')

@public_bp.route('/sitemap')
def sitemap(): return render_template('public/sitemap.html')
""",
    "app/blueprints/support.py": """from flask import Blueprint, render_template, redirect, url_for, flash, session
from app.forms.support_forms import TicketForm
from app.services.support_service import SupportService
from app.utils import login_required

support_bp = Blueprint('support', __name__)

@support_bp.route('/help-center')
def help_center(): return render_template('support/help_center.html')

@support_bp.route('/knowledge-base')
def knowledge_base(): return render_template('support/knowledge_base.html')

@support_bp.route('/tickets', methods=['GET'])
@login_required
def my_tickets():
    svc = SupportService()
    tickets = svc.ticket_repo.get_user_tickets(session['user_id'])
    return render_template('support/my_tickets.html', tickets=tickets)

@support_bp.route('/tickets/new', methods=['GET', 'POST'])
@login_required
def new_ticket():
    form = TicketForm()
    if form.validate_on_submit():
        svc = SupportService()
        svc.raise_ticket(session['user_id'], form.category.data, form.priority.data, form.subject.data, form.description.data)
        flash('Ticket created successfully.', 'success')
        return redirect(url_for('support.my_tickets'))
    return render_template('support/raise_ticket.html', form=form)
""",
    "app/templates/public/landing.html": """{% extends 'base.html' %}
{% block content %}
<div class="row align-items-center py-5">
    <div class="col-md-6">
        <h1 class="display-4 fw-bold text-primary">Your Health, Secured in the Cloud</h1>
        <p class="lead">MedTrack provides state-of-the-art healthcare management, connecting patients and top specialists seamlessly.</p>
        <a href="{{ url_for('auth.register_patient') }}" class="btn btn-primary btn-lg mt-3">Get Started</a>
        <a href="{{ url_for('public.for_doctors') }}" class="btn btn-outline-secondary btn-lg mt-3 ms-2">For Doctors</a>
    </div>
    <div class="col-md-6 text-center">
        <!-- Hero placeholder -->
        <div class="bg-light p-5 rounded-3 shadow-sm border"><h3>Medical Professional Network</h3><p>Trusted by thousands.</p></div>
    </div>
</div>
<div class="py-5 bg-light rounded-3 px-4 mb-5">
    <h2 class="text-center mb-4">Top Specializations</h2>
    <div class="row text-center">
        <div class="col-md-3 p-3"><div class="card p-4 shadow-sm border-0"><h4>Cardiology</h4></div></div>
        <div class="col-md-3 p-3"><div class="card p-4 shadow-sm border-0"><h4>Neurology</h4></div></div>
        <div class="col-md-3 p-3"><div class="card p-4 shadow-sm border-0"><h4>Pediatrics</h4></div></div>
        <div class="col-md-3 p-3"><div class="card p-4 shadow-sm border-0"><h4>Orthopedics</h4></div></div>
    </div>
</div>
{% endblock %}""",
    "app/templates/public/about.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4 text-primary">About Us</h1>
<p class="lead">MedTrack was founded to bridge the gap between healthcare providers and patients using cloud-native technologies.</p>
<hr>
<h3>Our Mission</h3>
<p>To deliver an unparalleled, secure, and accessible healthcare management platform.</p>
<h3>Our Team</h3>
<p>We are a dedicated group of healthcare professionals, cloud architects, and security experts ensuring your data is handled with the utmost care.</p>
{% endblock %}""",
    "app/templates/public/services.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4 text-primary">Our Services</h1>
<ul>
    <li><strong>Telemedicine Consultations:</strong> Connect with specialists globally.</li>
    <li><strong>Digital Health Records:</strong> Secure, persistent, and HIPAA-compliant storage.</li>
    <li><strong>e-Prescriptions:</strong> Instantly available and verifiable digital prescriptions.</li>
</ul>
{% endblock %}""",
    "app/templates/public/how_it_works.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4 text-primary">How It Works</h1>
<ol class="lead">
    <li><strong>Register:</strong> Create a secure account in seconds.</li>
    <li><strong>Find a Doctor:</strong> Use our advanced filters to find the right specialist.</li>
    <li><strong>Book & Consult:</strong> Schedule an appointment and manage your records.</li>
</ol>
{% endblock %}""",
    "app/templates/public/for_doctors.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4 text-primary">For Doctors</h1>
<p class="lead">Join a rapidly growing network of verified medical professionals.</p>
<p>Why MedTrack?</p>
<ul>
    <li>Automated scheduling and queue management.</li>
    <li>Secure patient history access.</li>
    <li>Automated billing and invoices.</li>
</ul>
<a href="{{ url_for('auth.register_doctor') }}" class="btn btn-primary">Apply Now</a>
{% endblock %}""",
    "app/templates/public/contact.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4 text-primary">Contact Us</h1>
<div class="row">
    <div class="col-md-6">
        <form method="POST">
            {{ form.hidden_tag() }}
            {{ form.name.label(class="form-label") }} {{ form.name(class="form-control mb-3") }}
            {{ form.email.label(class="form-label") }} {{ form.email(class="form-control mb-3") }}
            {{ form.subject.label(class="form-label") }} {{ form.subject(class="form-control mb-3") }}
            {{ form.message.label(class="form-label") }} {{ form.message(class="form-control mb-3") }}
            {{ form.submit(class="btn btn-primary") }}
        </form>
    </div>
</div>
{% endblock %}""",
    "app/templates/public/faq.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4 text-primary">Frequently Asked Questions</h1>
<input type="text" id="faqSearch" onkeyup="searchFAQ()" placeholder="Search FAQs..." class="form-control mb-4">
<div class="accordion" id="faqAccordion">
    <div class="accordion-item">
        <h2 class="accordion-header"><button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#collapseOne">How do I book an appointment?</button></h2>
        <div id="collapseOne" class="accordion-collapse collapse show"><div class="accordion-body">Once logged in as a patient, navigate to 'Find Doctors' and select an available slot.</div></div>
    </div>
    <div class="accordion-item">
        <h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseTwo">Is my data secure?</button></h2>
        <div id="collapseTwo" class="accordion-collapse collapse"><div class="accordion-body">Yes. We use AWS server-side encryption and strict IAM least-privilege roles to protect your medical records.</div></div>
    </div>
</div>
<script>
function searchFAQ() {
    let filter = document.getElementById('faqSearch').value.toUpperCase();
    let items = document.getElementsByClassName('accordion-item');
    for (let i = 0; i < items.length; i++) {
        let txtValue = items[i].textContent || items[i].innerText;
        if (txtValue.toUpperCase().indexOf(filter) > -1) {
            items[i].style.display = "";
        } else {
            items[i].style.display = "none";
        }
    }
}
</script>
{% endblock %}""",
    "app/templates/public/legal_terms.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Terms & Conditions</h1>
<div class="alert alert-warning">[TEMPLATE FOR LEGAL REVIEW]</div>
<p><strong>1. Acceptance of Terms:</strong> By accessing MedTrack, you agree to these terms.</p>
<p><strong>2. User Accounts:</strong> You are responsible for maintaining the confidentiality of your password.</p>
<p><strong>3. Medical Disclaimer:</strong> MedTrack provides a platform for connecting with doctors; we do not directly provide medical advice.</p>
{% endblock %}""",
    "app/templates/public/legal_privacy.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Privacy Policy</h1>
<div class="alert alert-warning">[TEMPLATE FOR LEGAL REVIEW]</div>
<p>We are committed to protecting your privacy. We collect personal details and health data solely for providing healthcare services.</p>
<p>We do not sell your data to third parties. All data is encrypted at rest using industry-standard AES-256 encryption.</p>
{% endblock %}""",
    "app/templates/public/legal_data-protection.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Data Protection (DPDP Act & HIPAA Notice)</h1>
<div class="alert alert-warning">[TEMPLATE FOR LEGAL REVIEW]</div>
<p><strong>Data Fiduciary Notice:</strong> Under the India DPDP Act 2023, MedTrack acts as a Data Fiduciary. You have the right to access, correct, and erase your personal data.</p>
<p><strong>HIPAA Compliance:</strong> Protected Health Information (PHI) is safeguarded according to HIPAA guidelines, including strict access controls, audit logs, and encrypted transit.</p>
{% endblock %}""",
    "app/templates/public/legal_cookies.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Cookie Policy</h1>
<p>We use session cookies to maintain your login state. We do not use third-party tracking cookies.</p>
{% endblock %}""",
    "app/templates/public/legal_disclaimer.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Medical Disclaimer</h1>
<p>The content provided on MedTrack is for informational purposes. In a medical emergency, call your local emergency services immediately.</p>
{% endblock %}""",
    "app/templates/public/legal_refund.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Refund & Cancellation Policy</h1>
<p>Appointments cancelled at least 24 hours in advance will receive a full refund. No-shows are non-refundable.</p>
{% endblock %}""",
    "app/templates/public/legal_accessibility.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Accessibility Statement</h1>
<p>MedTrack is committed to digital accessibility. We adhere to WCAG 2.1 AA guidelines to ensure our platform is usable by everyone.</p>
{% endblock %}""",
    "app/templates/public/sitemap.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Sitemap</h1>
<ul>
    <li><a href="/">Home</a></li>
    <li><a href="/about">About</a></li>
    <li><a href="/contact">Contact</a></li>
    <li><a href="/faq">FAQ</a></li>
</ul>
{% endblock %}""",
    "app/templates/support/help_center.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Help Center</h1>
<a href="{{ url_for('support.knowledge_base') }}" class="btn btn-outline-primary">Knowledge Base</a>
<a href="{{ url_for('support.new_ticket') }}" class="btn btn-primary">Raise a Ticket</a>
{% endblock %}""",
    "app/templates/support/knowledge_base.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Knowledge Base</h1>
<p>Browse our articles on how to use MedTrack.</p>
<ul>
    <li><a href="#">How to reset my password?</a></li>
    <li><a href="#">Uploading medical records safely</a></li>
</ul>
{% endblock %}""",
    "app/templates/support/raise_ticket.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">Raise Support Ticket</h1>
<form method="POST" class="w-50">
    {{ form.hidden_tag() }}
    {{ form.category.label(class="form-label") }} {{ form.category(class="form-select mb-3") }}
    {{ form.priority.label(class="form-label") }} {{ form.priority(class="form-select mb-3") }}
    {{ form.subject.label(class="form-label") }} {{ form.subject(class="form-control mb-3") }}
    {{ form.description.label(class="form-label") }} {{ form.description(class="form-control mb-3") }}
    {{ form.submit(class="btn btn-primary") }}
</form>
{% endblock %}""",
    "app/templates/support/my_tickets.html": """{% extends 'base.html' %}{% block content %}
<h1 class="mb-4">My Tickets</h1>
<table class="table">
    <tr><th>Subject</th><th>Category</th><th>Priority</th><th>Status</th><th>Date</th></tr>
    {% for ticket in tickets %}
    <tr><td>{{ ticket.Subject }}</td><td>{{ ticket.Category }}</td><td>{{ ticket.Priority }}</td><td><span class="badge bg-secondary">{{ ticket.Status }}</span></td><td>{{ ticket.CreatedAt }}</td></tr>
    {% endfor %}
</table>
{% endblock %}""",
    "tests/test_public.py": """import pytest

def test_public_pages(client):
    pages = ['/', '/about', '/services', '/how-it-works', '/for-doctors', '/faq', '/legal/terms', '/legal/privacy', '/legal/data-protection']
    for p in pages:
        res = client.get(p)
        assert res.status_code == 200

def test_contact_form(client, dynamodb_setup):
    res = client.post('/contact', data={
        'name': 'Tester', 'email': 'test@test.com', 'subject': 'Help', 'message': 'I need help', 'submit': True
    }, follow_redirects=True)
    assert b'Your message has been sent' in res.data
"""
}

# Ensure base.html has the links updated in the footer
import re
with open('app/templates/base.html', 'r', encoding='utf-8') as f:
    base_html = f.read()

footer_replacement = '''<footer class="bg-light py-4 mt-auto border-top">
    <div class="container text-center text-muted">
        <div class="mb-2">
            <a href="/legal/terms" class="text-muted text-decoration-none mx-2">Terms</a>
            <a href="/legal/privacy" class="text-muted text-decoration-none mx-2">Privacy</a>
            <a href="/legal/data-protection" class="text-muted text-decoration-none mx-2">Data Protection</a>
            <a href="/faq" class="text-muted text-decoration-none mx-2">FAQ</a>
            <a href="/support/help-center" class="text-muted text-decoration-none mx-2">Help Center</a>
        </div>
        <small>&copy; 2026 MedTrack. All rights reserved.</small>
    </div>
</footer>'''

# Naive replace footer
base_html = re.sub(r'<footer.*?</footer>', footer_replacement, base_html, flags=re.DOTALL)

with open('app/templates/base.html', 'w', encoding='utf-8') as f:
    f.write(base_html)

for path, content in files.items():
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
