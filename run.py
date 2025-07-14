import os
from main import create_app

# Get environment
env = os.environ.get('FLASK_ENV', 'development')

# Create app with proper config
app = create_app(env)

if __name__ == '__main__':
    # Run the app
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5001)),
        debug=env == 'development'
    ) 