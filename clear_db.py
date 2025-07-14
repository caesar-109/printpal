from main import create_app
from models import db, User, PrintRequest

def clear_database():
    app = create_app()
    
    with app.app_context():
        try:
            # Delete all print requests
            PrintRequest.query.delete()
            
            # Delete all users except faculty1
            User.query.filter(User.username != 'faculty1').delete()
            
            # Commit the changes
            db.session.commit()
            print("Database cleared successfully!")
            print("All print requests and student accounts have been removed.")
            print("Default faculty account (faculty1) has been preserved.")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error clearing database: {str(e)}")
            
if __name__ == '__main__':
    # Ask for confirmation
    confirm = input("This will delete all print requests and student accounts. Are you sure? (y/N): ")
    
    if confirm.lower() == 'y':
        clear_database()
    else:
        print("Operation cancelled.") 