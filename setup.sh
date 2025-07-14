#!/bin/bash

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies using pip
pip install -r requirements.txt

# Create logs directory
mkdir -p logs

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOL
FLASK_ENV=development
FLASK_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/printpal_dev
EOL
fi

# Check if PostgreSQL is running
if ! pg_isready > /dev/null 2>&1; then
    echo "PostgreSQL is not running. Starting PostgreSQL..."
    brew services start postgresql@15 || {
        echo "Failed to start PostgreSQL. Please install it first:"
        echo "brew install postgresql@15"
        exit 1
    }
    # Wait for PostgreSQL to start
    sleep 5
fi

# Create PostgreSQL user if it doesn't exist
if ! psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='postgres'" | grep -q 1; then
    echo "Creating PostgreSQL user 'postgres'..."
    createuser -s postgres || echo "User postgres may already exist"
fi

# Set password for postgres user
psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';" || echo "Could not set password (may already be set)"

# Create database
echo "Creating database..."
createdb -U postgres printpal_dev || echo "Database may already exist"

# Initialize database
echo "Initializing database..."
python3 init_db.py

echo "Setup complete! You can now run the application with:"
echo "python3 run.py" 