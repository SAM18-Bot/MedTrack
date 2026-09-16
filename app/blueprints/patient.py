from flask import Blueprint
patient_bp = Blueprint('patient', __name__)
@patient_bp.route('/dashboard')
def dashboard(): return 'Patient Dashboard'