from main import create_app
from models import db, User
import os

# Create the Flask application1
app = create_app('production')

# Database initialization endpoint (only available during setup)
@app.route('/api/init')
def init_database():
    if not os.environ.get('VERCEL'):
        return 'Not allowed', 403
        
    try:
        with app.app_context():
            # Create all tables
            db.create_all()
            
            # Create default faculty user if it doesn't exist
            if not User.query.filter_by(username='faculty1').first():
                faculty = User(username='faculty1', role='faculty')
                faculty.set_password('adminpass')
                db.session.add(faculty)
                db.session.commit()
                return 'Database initialized successfully! You can now log in with faculty1/adminpass'
            return 'Database already initialized!'
    except Exception as e:
        return f'Error initializing database: {str(e)}', 500

# For local development
if __name__ == '__main__':
    app.run() 
