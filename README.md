# Gas Platform Backend

A FastAPI backend for the Gas Platform with PostgreSQL database, SQLAlchemy ORM, and JWT authentication.

## Tech Stack

- FastAPI + PostgreSQL + SQLAlchemy + Alembic
- Auth: JWT via `python-jose`
- Hashing: `passlib[bcrypt]`
- Config: `.env` using `python-dotenv`

## Prerequisites

1. PostgreSQL installed and running
2. Python 3.8 or higher
3. Poetry or pip for package management

## Project Structure

```
app/
├── core/           # Configuration
├── db/            # Database sessions and connections
├── models/        # SQLAlchemy models
├── routes/        # API endpoints
├── schemas/       # Pydantic models
└── utils/         # Utility functions
```

## Initial Setup

1. Install and configure PostgreSQL:
   ```bash
   # Install PostgreSQL (if not already installed)
   sudo apt-get update
   sudo apt-get install postgresql postgresql-contrib

   # Start PostgreSQL service
   sudo service postgresql start

   # Create a PostgreSQL user (if needed)
   sudo -u postgres createuser --interactive --pwprompt

   # Create the database
   sudo -u postgres createdb gas_platform
   ```

2. Create and activate virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   # Create .env file from example
   cp .env.example .env
   
   # Edit .env file with your database credentials and settings
   # Make sure to update POSTGRES_USER and POSTGRES_PASSWORD
   # with the values you set when creating the PostgreSQL user
   ```

5. Run database migrations:
   ```bash
   # Set PYTHONPATH
   export PYTHONPATH=$PYTHONPATH:/path/to/gasPlatform

   # Run migrations
   alembic upgrade head
   ```

6. Start the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:
- Interactive API documentation (Swagger UI): `http://localhost:8000/docs`
- Alternative API documentation (ReDoc): `http://localhost:8000/redoc`

## API Endpoints

The API uses `/api/v1` versioning. Available endpoints:

### Users
- `POST /api/v1/users/` - Create a new user
- `GET /api/v1/users/` - List all users
- `GET /api/v1/users/{user_id}` - Get specific user

## Development

To create a new database migration:
```bash
alembic revision --autogenerate -m "description of changes"
```

To apply migrations:
```bash
alembic upgrade head
```

## Current Status

The project structure and all necessary files have been created, but the following steps are needed to get the application running:

1. PostgreSQL needs to be installed and configured
2. A database user needs to be created with appropriate permissions
3. The database needs to be created
4. The .env file needs to be updated with the correct database credentials
5. Database migrations need to be run

Please follow the Initial Setup instructions above to complete the setup.
