from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SubmitField, TextAreaField, FloatField
from wtforms.validators import DataRequired, Optional

class ProfileForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    dob = StringField('Date of Birth (YYYY-MM-DD)', validators=[Optional()])
    gender = SelectField('Gender', choices=[('', 'Select'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], validators=[Optional()])
    blood_group = SelectField('Blood Group', choices=[('', 'Select'), ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'), ('O+', 'O+'), ('O-', 'O-'), ('AB+', 'AB+'), ('AB-', 'AB-')], validators=[Optional()])
    height = FloatField('Height (cm)', validators=[Optional()])
    weight = FloatField('Weight (kg)', validators=[Optional()])
    address = TextAreaField('Address', validators=[Optional()])
    emergency_contact = StringField('Emergency Contact', validators=[Optional()])
    insurance_provider = StringField('Insurance Provider', validators=[Optional()])
    policy_number = StringField('Policy Number', validators=[Optional()])
    allergies = StringField('Allergies (comma-separated)', validators=[Optional()])
    chronic_conditions = StringField('Chronic Conditions (comma-separated)', validators=[Optional()])
    submit = SubmitField('Update Profile')

class DoctorSearchForm(FlaskForm):
    specialization = StringField('Specialization', validators=[Optional()])
    city = StringField('City', validators=[Optional()])
    max_fee = FloatField('Max Fee', validators=[Optional()])
    submit = SubmitField('Search')

class BookingForm(FlaskForm):
    date = StringField('Date (YYYY-MM-DD)', validators=[DataRequired()])
    time = StringField('Time (HH:MM)', validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Confirm Booking')

class VitalsForm(FlaskForm):
    blood_pressure = StringField('Blood Pressure (e.g. 120/80)', validators=[DataRequired()])
    sugar_level = FloatField('Sugar Level (mg/dL)', validators=[DataRequired()])
    weight = FloatField('Weight (kg)', validators=[DataRequired()])
    heart_rate = IntegerField('Heart Rate (bpm)', validators=[DataRequired()])
    submit = SubmitField('Log Vitals')

from flask_wtf.file import FileField, FileAllowed, FileRequired
class DocumentUploadForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    document = FileField('Document', validators=[FileRequired(), FileAllowed(['pdf', 'png', 'jpg'], 'PDF or Images only!')])
    submit = SubmitField('Upload')

