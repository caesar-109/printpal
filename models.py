from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student', 'faculty', 'admin'
    name = db.Column(db.String(100))
    branch = db.Column(db.String(100), nullable=True)
    semester = db.Column(db.String(2), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationship with print requests
    print_requests = db.relationship('PrintRequest', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_student(self):
        return self.role == 'student'
    
    def is_faculty(self):
        return self.role == 'faculty'
    
    def is_admin(self):
        return self.role == 'admin'
    
    def can_use_print_service(self):
        return self.is_active and (not self.is_student() or self.is_verified)

class PrintRequest(db.Model):
    __tablename__ = 'print_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def student_name(self):
        return self.user.name
        
    @property
    def student_class(self):
        return self.user.student_class 

class SystemStatus(db.Model):
    __tablename__ = 'system_status'
    
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reason = db.Column(db.String(200), nullable=True) 