from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, ValidationError, Regexp, EqualTo
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=80)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6)
    ])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=4, max=20),
        Regexp(r'^[\w.@+-]+$', message='Username contains invalid characters')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password')
    ])
    name = StringField('Full Name', validators=[
        DataRequired(),
        Length(max=100)
    ])
    
    branch_choices = [
        ('AD', 'Artificial Intelligence and Data Science'),
        ('CE', 'Civil Engineering'),
        ('CSD', 'Computer Science and Design'),
        ('CSE-A', 'Computer Science and Engineering - A'),
        ('CSE-B', 'Computer Science and Engineering - B'),
        ('CSE-C', 'Computer Science and Engineering - C'),
        ('ECE', 'Electronics and Communication Engineering'),
        ('EEE', 'Electrical and Electronics Engineering'),
        ('IT', 'Information Technology'),
        ('ME', 'Mechanical Engineering')
    ]

    year_choices = [
        ('2022', '2022'),
        ('2023', '2023'),
        ('2024', '2024'),
        ('2025', '2025'),
    ]

    semester_choices = [
        ('S1', 'S1'),
        ('S2', 'S2'),
        ('S3', 'S3'),
        ('S4', 'S4'),
        ('S5', 'S5'),
        ('S6', 'S6'),
        ('S7', 'S7'),
        ('S8', 'S8')
    ]
    
    branch = SelectField('Branch', choices=branch_choices, validators=[DataRequired()])
    year = SelectField('Year', choices=year_choices, validators=[DataRequired()])
    semester = SelectField('Semester', choices=semester_choices, validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already exists.')

class ProfileUpdateForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=4, max=20),
        Regexp(r'^[\w.@+-]+$', message='Username contains invalid characters')
    ])
    name = StringField('Full Name', validators=[
        DataRequired(),
        Length(max=100)
    ])
    
    branch_choices = [
        ('AD', 'Artificial Intelligence and Data Science'),
        ('CE', 'Civil Engineering'),
        ('CSD', 'Computer Science and Design'),
        ('CSE-A', 'Computer Science and Engineering - A'),
        ('CSE-B', 'Computer Science and Engineering - B'),
        ('CSE-C', 'Computer Science and Engineering - C'),
        ('ECE', 'Electronics and Communication Engineering'),
        ('EEE', 'Electrical and Electronics Engineering'),
        ('IT', 'Information Technology'),
        ('ME', 'Mechanical Engineering')
    ]
    
    semester_choices = [
        ('S1', 'S1'), ('S2', 'S2'), ('S3', 'S3'), ('S4', 'S4'),
        ('S5', 'S5'), ('S6', 'S6'), ('S7', 'S7'), ('S8', 'S8')
    ]
    
    branch = SelectField('Branch', choices=branch_choices, validators=[DataRequired()])
    semester = SelectField('Semester', choices=semester_choices, validators=[DataRequired()])
    submit = SubmitField('Save Changes')

    def __init__(self, original_username, *args, **kwargs):
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, field):
        if field.data != self.original_username:
            if User.query.filter_by(username=field.data).first():
                raise ValidationError('Username already exists.')

class PasswordChangeForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Change Password') 