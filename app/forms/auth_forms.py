from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo, Regexp

EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
EMAIL_MESSAGE = "Please enter a valid email address."

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(message="Email is required."), Regexp(EMAIL_REGEX, message=EMAIL_MESSAGE)])
    password = PasswordField('Password', validators=[DataRequired(message="Password is required.")])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')

class PatientRegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Regexp(EMAIL_REGEX, message=EMAIL_MESSAGE)])
    phone = StringField('Phone', validators=[DataRequired(), Regexp(r'^\+?1?\d{9,15}$', message="Invalid phone number.")])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters.")])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register as Patient')

class DoctorRegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Regexp(EMAIL_REGEX, message=EMAIL_MESSAGE)])
    phone = StringField('Phone', validators=[DataRequired()])
    specialization = StringField('Specialization', validators=[DataRequired()])
    registration_number = StringField('Medical Registration Number', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register as Doctor')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Regexp(EMAIL_REGEX, message=EMAIL_MESSAGE)])
    submit = SubmitField('Send OTP')

class ResetPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Regexp(EMAIL_REGEX, message=EMAIL_MESSAGE)])
    otp = StringField('OTP', validators=[DataRequired(), Length(min=6, max=6)])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Reset Password')
