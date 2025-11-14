# **Improve API Service**

**Improve API Service** — is a backend system for managing user transactions, accounts, and reporting. The service handles deposits, withdrawals, transaction rollbacks, account freezing, and generates weekly reports with analytics on user activity and financial operations.

![FastAPI](https://img.shields.io/badge/FastAPI-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)
![Docker](https://img.shields.io/badge/Docker-✓-blue)
![Poetry](https://img.shields.io/badge/Poetry-2.2.1-purple)

---

⚙️ Tech Stack

- **Backend:** FastAPI  
- **Database:** PostgreSQL  
- **ORM:** SQLAlchemy + Alembic  
- **Asynchrony:** Uvicorn (ASGI)  
- **Containerization:** Docker, Docker Compose  
- **Dependency Management:** Poetry  
- **Code Quality & Linting:** flake8, black, isort, mypy  
- **Testing:** Pytest  
- **Development Tools:** Makefile commands

---

## 🚀 Quick Start

### 📁 Clone the Repository

```bash
git clone https://github.com/TekkenBro7/improve-api-service.git
cd improve-api-service
```

### ⚙️ Setup `.env` File

Create a `.env` file in your root based on `.env.example`

### Installing dependencies via Poetry

Install Poetry if not already installed:
```bash
pip install poetry
```

Install project dependencies
```bash
poetry install
```

Before making any commits, run the following command to set up the pre-commit hooks:
```bash
poetry run pre-commit install
```

To test pre-commit hooks without a commit, use
```bash
make lint
```
### 🛠️ Alembic Migrations
Once your database is configured and the **.env** file is ready, you need to apply migrations using Alembic to create the necessary tables and schema.

### 📌 Creating a New Migration
To generate a new migration after updating or adding models:
```bash
poetry run alembic revision --autogenerate -m "your message here"
```
This will create a new file in the database/alembic/versions/ directory containing the migration script.

### ✅ Applying Migrations
To apply the latest migration to your database:

```bash
poetry run alembic upgrade head
```
This ensures your database schema is up to date with the current models. If you run it through docker, it will automatically apply migrations.

### 🐳 Running with Docker

To start the app using Docker:
```bash
docker-compose up --build
```
And make sure that the `env` file states `POSTGRES_HOST=db`

- FastAPI will run on `http://localhost:8000`
- PostgreSQL is available at port `5432`

### 🔧 Run Locally

1. Ensure PostgreSQL are installed and running
2. Create a PostgreSQL database and grant privileges users `.env` variables like
```bash
CREATE DATABASE 'your_db';
CREATE USER 'your_user' WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE 'your_db' TO 'your_user';
```
3. Apply migrations
4. Ensure `.env` specifies `POSTGRES_HOST=localhost`
5. Start the development server
```bash
make runserver
```
