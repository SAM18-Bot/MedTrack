from flask import Blueprint
doctor_bp = Blueprint('doctor', __name__)
@doctor_bp.route('/dashboard')
def dashboard(): return 'Doctor Dashboard'