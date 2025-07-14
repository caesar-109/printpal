from main import create_app
from models import db, User

def init_database():
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create default faculty user if it doesn't exist
        if not User.query.filter_by(username='faculty1').first():
            faculty = User(username='faculty1', role='faculty')
            faculty.set_password('adminpass')
            db.session.add(faculty)
            
            # Create default student user
            student = User(
                username='student1',
                role='student',
                name='John Doe',
                student_class='CS-101'
            )
            student.set_password('password123')
            db.session.add(student)
            
            try:
                db.session.commit()
                print("Database initialized successfully!")
            except Exception as e:
                db.session.rollback()
                print(f"Error initializing database: {str(e)}")

if __name__ == '__main__':
    init_database() 