from main import create_app
from models import db, User

def init_neon_database():
    # Create app with production config to use Neon DB
    app = create_app('production')
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create default faculty user if it doesn't exist
        if not User.query.filter_by(username='faculty1').first():
            faculty = User(username='faculty1', role='faculty')
            faculty.set_password('adminpass')
            db.session.add(faculty)
            
            try:
                db.session.commit()
                print("✓ Faculty account created successfully!")
            except Exception as e:
                db.session.rollback()
                print(f"✗ Error creating faculty account: {str(e)}")
                return
        
        print("✓ Database initialized successfully!")
        print("\nDefault credentials:")
        print("Faculty:")
        print("  Username: faculty1")
        print("  Password: adminpass")

if __name__ == '__main__':
    print("Initializing Neon database...")
    init_neon_database() 