from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import EmailField, PasswordField, SubmitField, StringField, DateField, SelectField, URLField, \
    TextAreaField, FileField
from wtforms.validators import DataRequired, Email, optional, Optional

from wtforms.validators import ValidationError

def deadline_after_applied(form, field):
    if field.data and form.date_applied.data:
        if field.data < form.date_applied.data:
            raise ValidationError("Deadline cannot be before the date applied.")
#1. In forms.py, build a RegisterForm with email and password fields, using validators like DataRequired and Email.
class RegisterForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')
#3. Build a LoginForm and the /login route: look up the user by email, verify the password with check_password_hash, then call login_user(user).
class LoginForm(FlaskForm):
    email = EmailField('Email',validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')
#company (StringField), role (StringField), date_applied (DateField), status (SelectField), job_link (URLField), notes (TextAreaField).
class ApplicationForm(FlaskForm):
    company = StringField('Company', validators=[DataRequired()])
    role = StringField('Role', validators=[DataRequired()])
    date_applied = DateField('Date Applied', validators=[DataRequired()])
    deadline = DateField('Deadline', validators=[Optional(), deadline_after_applied])
    #Applied, OA/Test, Interview, Offer, Rejected
    status = SelectField(
        'Status',
        choices=[
            ('Applied', 'Applied'),
            ('OA/Test', 'OA/Test'),
            ('Interview', 'Interview'),
            ('Offer', 'Offer'),
            ('Rejected', 'Rejected')
        ]
    )
    job_link = URLField('Job Link', validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[DataRequired()])
    file = FileField('File', validators=[FileAllowed(['pdf', 'docx']) ])
    submit = SubmitField('Submit')
