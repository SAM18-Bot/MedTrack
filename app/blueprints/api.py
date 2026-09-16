from flask import Blueprint, jsonify
from app.utils import login_required, role_required

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.before_request
@login_required
@role_required('Admin')
def before_request():
    pass

@api_bp.route('/export-data')
def export_data():
    return jsonify({"status": "Exporting data... (Mocked for safety)"})
