# PrintPal - Print Request Management System

A Flask-based web application for managing print requests in an educational institution.

## Tech Stack

### Backend
- Python 3.11+
- Flask (Web framework)
- PostgreSQL (Database)
- SQLAlchemy (ORM)
- Flask-Login (Authentication)
- Flask-WTF (Forms and CSRF)
- Gunicorn (WSGI server)

### Frontend
- React 18
- TypeScript
- Tailwind CSS
- React Query
- React Router
- Vite (Build tool)

### Development & Testing
- Bun (Package manager & runtime)
- Jest (Testing)
- ESLint (Linting)
- Prettier (Code formatting)
- PyTest (Python testing)

## Features

- User authentication with role-based access control (Student/Faculty)
- Student print request management
- Faculty request approval system
- Daily request limits
- Request history with pagination
- Export functionality for request data
- Secure session management
- Rate limiting
- Input validation and sanitization

## Prerequisites

- Python 3.11 or higher
- PostgreSQL database
- Bun runtime (for package management and development)
- Node.js 18+ (for certain build tools)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/printpal.git
cd printpal
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
bun install
```

4. Set up the PostgreSQL database:
```bash
createdb printpal_dev
```

5. Set environment variables (create a .env file):
```bash
FLASK_ENV=development
FLASK_SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://postgres:postgres@localhost/printpal_dev
```

6. Initialize the database:
```bash
python init_db.py
```

## Development

1. Start the backend development server:
```bash
python run.py
```

2. Start the frontend development server:
```bash
bun dev
```

3. Run tests:
```bash
# Backend tests
pytest

# Frontend tests
bun test
```

4. Lint and format code:
```bash
# Backend
black .
flake8 .

# Frontend
bun lint
bun format
```

## Project Structure

```
printpal/
├── backend/
│   ├── api/            # API routes
│   ├── models/         # Database models
│   ├── services/       # Business logic
│   └── utils/          # Helper functions
├── frontend/
│   ├── src/
│   │   ├── components/ # React components
│   │   ├── pages/      # Page components
│   │   ├── hooks/      # Custom hooks
│   │   └── utils/      # Helper functions
│   └── public/         # Static assets
├── tests/              # Test files
└── docs/              # Documentation
```

## API Documentation

API documentation is available at `/api/docs` when running the development server. For detailed API specifications, see the [API Documentation](./docs/API.md).

## Deployment

### Docker Deployment
```bash
# Build the Docker image
docker build -t printpal .

# Run the container
docker run -p 8000:8000 printpal
```

### Manual Deployment
1. Build the frontend:
```bash
bun run build
```

2. Set up production environment variables
3. Run database migrations
4. Start the production server:
```bash
gunicorn --bind 0.0.0.0:5000 "main:create_app('production')"
```

## Default Users

The system comes with two default users for testing:

1. Faculty:
   - Username: faculty1
   - Password: adminpass

2. Student:
   - Username: student1
   - Password: password123

## Security Features

- CSRF protection
- Password hashing
- Rate limiting
- Session security
- Input validation
- SQL injection prevention

## Monitoring & Logging

- Application logs are stored in `/var/log/printpal/`
- Monitoring dashboard available at `/admin/monitoring`
- Prometheus metrics exposed at `/metrics`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 