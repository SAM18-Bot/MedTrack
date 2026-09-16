from flask import Blueprint, render_template, redirect, url_for, flash
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
