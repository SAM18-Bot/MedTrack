from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, FloatField, SubmitField
from wtforms.validators import DataRequired, Optional

class DoctorProfileForm(FlaskForm):
    bio = TextAreaField('Bio', validators=[Optional()])
    clinic_address = TextAreaField('Clinic Address', validators=[Optional()])
    consultation_fee = FloatField('Consultation Fee ($)', validators=[Optional()])
    experience_years = IntegerField('Years of Experience', validators=[Optional()])
    qualifications = StringField('Qualifications (comma-separated)', validators=[Optional()])
    submit = SubmitField('Update Profile')

class AvailabilityForm(FlaskForm):
    date = StringField('Date (YYYY-MM-DD)', validators=[DataRequired()])
    start_time = StringField('Start Time (HH:MM)', validators=[DataRequired()])
    end_time = StringField('End Time (HH:MM)', validators=[DataRequired()])
    slot_duration = IntegerField('Slot Duration (minutes)', default=15, validators=[DataRequired()])
    submit = SubmitField('Set Availability')

class ConsultationForm(FlaskForm):
    symptoms = TextAreaField('Symptoms', validators=[DataRequired()])
    diagnosis = TextAreaField('Diagnosis', validators=[DataRequired()])
    medicines = TextAreaField('Medicines (JSON or text)', validators=[Optional()])
    notes = TextAreaField('Private Notes', validators=[Optional()])
    submit = SubmitField('Complete Consultation')
