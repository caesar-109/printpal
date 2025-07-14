from flask_migrate import Migrate
from main import create_app
from models import db

app = create_app()
migrate = Migrate(app, db)

if __name__ == '__main__':
    with app.app_context():
        migrate.init_app(app, db) 