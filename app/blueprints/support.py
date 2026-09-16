from flask import Blueprint, render_template, redirect, url_for, flash, session
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
