# 🏥 Clinic Management System

A comprehensive, production-ready clinic management system built with FastAPI, PostgreSQL, MongoDB, and Redis. This system handles patient management, appointments, visits, prescriptions, billing, inventory, and real-time queue management.

## ✨ Features

### 👥 Patient Management
- Patient registration with complete medical history
- Search patients by name, phone, or ID
- Track allergies, chronic conditions, and emergency contacts
- View complete visit history and prescriptions

### 📅 Appointment System
- Slot-based appointment scheduling
- Bulk slot creation for doctors
- Slot blocking for breaks/unavailability
- Appointment status tracking (SCHEDULED, WITH_DOCTOR, COMPLETED, CANCELLED)
- Walk-in patient support

### 🏥 Visit Management
- Record vitals (BP, temperature, pulse, weight, height)
- Chief complaints and diagnosis tracking
- Treatment plans
- Clinical notes with categories (symptom, observation, diagnosis, treatment)
- Visit history stored in MongoDB for fast retrieval

### 💊 Prescription & Pharmacy
- Digital prescriptions with medicine details
- Dosage, frequency, and duration tracking
- Prescription dispensing workflow
- Integration with inventory system
- Printable prescription format

### 💰 Billing & Invoicing
- **AUTO MODE**: Generate bill from prescription automatically
- **MANUAL MODE**: Custom billing for walk-ins
- Multiple payment methods (cash, card, UPI)
- Invoice status tracking (DRAFT, PENDING, PAID, CANCELLED)
- Automatic tax and discount calculations

### 📦 Inventory Management
- Medicine catalog with batch tracking
- Stock level monitoring with reorder alerts
- Expiry date tracking
- Stock movements logged in MongoDB
- Automatic inventory updates on dispensing

### 🔄 Queue Management (Redis-based)
- Real-time patient queue using Redis
- Token-based system
- Check-in for appointments and walk-ins
- Queue status updates (WAITING, WITH_DOCTOR, COMPLETED, SKIPPED)
- Daily queue summary and statistics

### 📊 Reports & Analytics
- Daily summaries stored in MongoDB
- Audit logs for all critical actions
- Visit history with prescriptions
- Stock movement reports

### 🔐 Authentication & Authorization
- JWT-based authentication
- Role-based access control (ADMIN, DOCTOR, PHARMACIST, RECEPTION)
- Secure password hashing with bcrypt
- Token expiration and refresh

## 🛠️ Tech Stack

### Backend
- **FastAPI** 0.115.5 - Modern, fast web framework
- **Python** 3.9+
- **Pydantic** - Data validation
- **SQLAlchemy** 2.0 - ORM with async support

### Databases
- **PostgreSQL** - Primary relational database
- **MongoDB** - Document storage for logs, history, and analytics
- **Redis** - Queue management and caching

### Tools
- **Alembic** - Database migrations
- **Uvicorn** - ASGI server
- **Docker** - Containerization
- **Motor** - Async MongoDB driver
- **asyncpg** - Async PostgreSQL driver

## 📋 Prerequisites

- Python 3.9 or higher
- Docker and Docker Compose
- PostgreSQL 13+
- MongoDB 5.0+
- Redis 7.0+

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd FASTAPI_PROJ
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start Docker Services

```bash
docker-compose up -d
```

This starts:
- PostgreSQL on port 5433
- MongoDB on port 27017
- Redis on port 6379

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```env
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://clinic_user:clinic_pass@localhost:5433/clinic_db

# MongoDB
MONGO_URL=mongodb://clinic_admin:clinic_mongo_pass@localhost:27017/

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 6. Run Database Migrations

```bash
alembic upgrade head
```

### 7. Start the Application

```bash
uvicorn app.main:app --reload
```

The API will be available at: `http://localhost:8000`

## 📚 API Documentation

Once the application is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🏗️ Project Structure

```
FASTAPI_PROJ/
├── app/
│   ├── routers/           # API endpoints
│   │   ├── auth.py        # Authentication
│   │   ├── patients.py    # Patient management
│   │   ├── appointments.py
│   │   ├── slots.py       # Appointment slots
│   │   ├── visits.py      # Visit management
│   │   ├── prescriptions.py
│   │   ├── inventory.py   # Medicine inventory
│   │   ├── dispensing.py  # Pharmacy
│   │   ├── billing.py     # Invoicing
│   │   ├── queue.py       # Queue management
│   │   └── reports.py     # Analytics
│   ├── services/          # Business logic
│   │   ├── queue_service.py
│   │   └── mongo_services.py
│   ├── models.py          # SQLAlchemy models
│   ├── schemas.py         # Pydantic schemas
│   ├── database.py        # PostgreSQL connection
│   ├── mongo_client.py    # MongoDB connection
│   ├── redis_client.py    # Redis connection
│   ├── auth.py            # Authentication logic
│   ├── config.py          # Configuration
│   └── main.py            # Application entry point
├── alembic/               # Database migrations
├── .env                   # Environment variables
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Docker services
└── README.md
```

## 🔑 Default Users

After running migrations, create users via API or use these roles:

| Role | Permissions |
|------|-------------|
| ADMIN | Full system access |
| DOCTOR | Patient records, visits, prescriptions |
| PHARMACIST | Inventory, dispensing, prescriptions |
| RECEPTION | Patients, appointments, queue |

## 🎯 Key API Endpoints

### Authentication
```
POST /auth/login          # Login and get JWT token
POST /auth/register       # Register new user (admin only)
```

### Patients
```
GET    /patients          # List patients (with search)
POST   /patients          # Create patient
GET    /patients/{id}     # Get patient details
PATCH  /patients/{id}     # Update patient
DELETE /patients/{id}     # Delete patient
```

### Appointments
```
GET  /appointments        # List appointments
POST /appointments        # Create appointment
GET  /appointments/{id}   # Get appointment
PATCH /appointments/{id}  # Update appointment
DELETE /appointments/{id} # Cancel appointment
```

### Visits
```
POST   /visits                    # Start visit
GET    /visits/{id}               # Get visit details
PATCH  /visits/{id}               # Update visit
POST   /visits/{id}/complete      # Complete visit
POST   /visits/{id}/notes         # Add clinical note
GET    /visits/{id}/notes         # Get clinical notes
```

### Prescriptions
```
POST   /prescriptions             # Create prescription
GET    /prescriptions/{id}        # Get prescription
GET    /prescriptions/{id}/print  # Printable format
```

### Billing
```
POST   /billing                   # Generate invoice
GET    /billing/{id}              # Get invoice
PATCH  /billing/{id}              # Update invoice
POST   /billing/{id}/pay          # Mark as paid
```

### Queue
```
POST   /queue/checkin             # Check-in patient
POST   /queue/walk-in             # Add walk-in patient
GET    /queue/today               # Get today's queue
POST   /queue/next                # Call next patient
PATCH  /queue/{token}/status      # Update token status
```

### Inventory
```
GET    /inventory/medicines       # List medicines
POST   /inventory/medicines       # Add medicine
GET    /inventory/low-stock       # Low stock alerts
POST   /inventory/batches         # Add batch
PATCH  /inventory/batches/{id}    # Update batch stock
```

## 🐳 Docker Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker logs clinic_postgres
docker logs clinic_mongo
docker logs clinic_redis

# Access MongoDB shell
docker exec -it clinic_mongo mongosh "mongodb://clinic_admin:clinic_mongo_pass@localhost:27017/clinic_logs?authSource=admin"

# Access Redis CLI
docker exec -it clinic_redis redis-cli

# Access PostgreSQL
docker exec -it clinic_postgres psql -U clinic_user -d clinic_db
```

## 🔍 MongoDB Collections

The system uses MongoDB for analytics and logging:

- **audit_logs** - All user actions (create, update, delete)
- **visit_history** - Complete visit records with prescriptions
- **stock_movements** - Inventory transactions
- **daily_summaries** - Daily statistics

View data:
```bash
# View audit logs
docker exec clinic_mongo mongosh "mongodb://clinic_admin:clinic_mongo_pass@localhost:27017/clinic_logs?authSource=admin" --quiet --eval "db.audit_logs.find().limit(5).pretty()"

# View visit history
docker exec clinic_mongo mongosh "mongodb://clinic_admin:clinic_mongo_pass@localhost:27017/clinic_logs?authSource=admin" --quiet --eval "db.visit_history.find().limit(5).pretty()"

# View stock movements
docker exec clinic_mongo mongosh "mongodb://clinic_admin:clinic_mongo_pass@localhost:27017/clinic_logs?authSource=admin" --quiet --eval "db.stock_movements.find().limit(5).pretty()"
```

## 📊 Redis Queue Keys

Queue data is stored in Redis:

- `queue:{date}` - Sorted set with queue order
- `queue:token:{date}:{number}` - Token details
- `queue:counter:{date}` - Token counter
- `queue:current:{date}` - Currently serving token

View queue:
```bash
# List all queue keys
docker exec clinic_redis redis-cli KEYS "queue:*"

# Get queue for today
docker exec clinic_redis redis-cli ZRANGE "queue:2026-02-17" 0 -1
```

## 🧪 Development

### Running Tests
```bash
pytest
```

### Database Migrations

Create new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback migration:
```bash
alembic downgrade -1
```

### Code Style
```bash
# Format code
black app/

# Lint code
flake8 app/
```

## 🔒 Security Features

- JWT token-based authentication
- Password hashing with bcrypt
- Role-based access control (RBAC)
- SQL injection protection via SQLAlchemy
- CORS middleware for API security
- Environment variable-based configuration
- Audit logging for all critical actions

## 📝 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | Required |
| MONGO_URL | MongoDB connection string | Required |
| REDIS_URL | Redis connection string | Required |
| SECRET_KEY | JWT secret key | Required |
| ALGORITHM | JWT algorithm | HS256 |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token expiration | 30 |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 👨‍💻 Author

Built with ❤️ using FastAPI

## 🙏 Acknowledgments

- FastAPI for the amazing framework
- SQLAlchemy for powerful ORM
- MongoDB for flexible document storage
- Redis for blazing-fast queue management

---

**Note**: This is a production-ready clinic management system. Ensure proper security measures, backups, and compliance with healthcare regulations (HIPAA, GDPR, etc.) before deploying to production.
