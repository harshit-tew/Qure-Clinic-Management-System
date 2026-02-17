# 🏥 Qure Clinic Management System

A complete, production-ready clinic management system with integrated pharmacy, real-time queue management, and comprehensive analytics.

**Tech Stack:** FastAPI • PostgreSQL • MongoDB • Redis • Docker

---

## 🎯 What This System Does

This is an all-in-one clinic management platform that handles:
- **Patient Management** - Registration, medical history, search
- **Appointments** - Slot-based scheduling with doctor availability
- **Queue System** - Real-time token-based queue (powered by Redis)
- **Consultations** - Record vitals, diagnosis, clinical notes
- **Prescriptions** - Digital prescriptions with dosage tracking
- **Pharmacy** - FIFO-based medicine dispensing
- **Billing** - Automated invoice generation with multiple payment methods
- **Inventory** - Medicine stock management with expiry tracking
- **Analytics** - Comprehensive audit logs and reports (powered by MongoDB)

---

## 📊 System Architecture

```mermaid
flowchart TB
    Client[👤 Client<br/>Web/Mobile App]

    subgraph API["⚡ FastAPI Backend"]
        Auth[🔐 JWT Authentication]
        Routes[📍 API Routes]
        Logic[💼 Business Logic]
    end

    subgraph DB["💾 Data Layer"]
        PG[(PostgreSQL<br/>Core Data)]
        Mongo[(MongoDB<br/>Logs & Analytics)]
        Redis[(Redis<br/>Queue)]
    end

    Client -->|HTTPS| Auth
    Auth --> Routes
    Routes --> Logic

    Logic <-->|Patients, Visits<br/>Prescriptions, Billing| PG
    Logic <-->|Audit Logs<br/>Visit History| Mongo
    Logic <-->|Real-time Queue| Redis

    style API fill:#e3f2fd
    style DB fill:#fff3e0
```

---

## 🔄 Complete Patient Flow

```mermaid
flowchart TD
    A[👤 Patient Arrives] --> B{Registered?}
    B -->|No| C[Register Patient]
    B -->|Yes| D{Has Appointment?}

    C --> D
    D -->|Yes| E[Check-in]
    D -->|No| F[Walk-in]

    E --> G[🎫 Join Queue<br/>Redis]
    F --> G

    G --> H[👨‍⚕️ Doctor Calls Next]
    H --> I[📋 Start Visit<br/>Record Vitals]

    I --> J[💊 Create Prescription]
    J --> K[💰 Generate Bill]

    K --> L[💳 Payment]
    L --> M{Has Medicines?}

    M -->|Yes| N[🏪 Dispense<br/>Update Stock FIFO]
    M -->|No| O[✅ Complete]
    N --> O

    style A fill:#4caf50,color:#fff
    style O fill:#2196f3,color:#fff
```

---

## 🗄️ Database Schema

```mermaid
erDiagram
    PATIENTS ||--o{ APPOINTMENTS : books
    PATIENTS ||--o{ VISITS : has
    PATIENTS ||--o{ INVOICES : receives

    APPOINTMENTS }|--|| SLOTS : uses
    SLOTS }|--|| USERS : "doctor"

    VISITS ||--|| PRESCRIPTIONS : generates
    VISITS }|--|| USERS : "doctor conducts"

    PRESCRIPTIONS ||--o{ PRESCRIPTION_ITEMS : contains
    PRESCRIPTION_ITEMS }|--|| MEDICINES : specifies

    MEDICINES ||--o{ MEDICINE_BATCHES : has

    PRESCRIPTIONS ||--o| INVOICES : "billed in"
    INVOICES ||--o| DISPENSING : triggers
    DISPENSING ||--o{ DISPENSING_ITEMS : contains
    DISPENSING_ITEMS }|--|| MEDICINE_BATCHES : "from"
```

**PostgreSQL** stores all core operational data
**MongoDB** stores audit logs, visit history, stock movements, daily summaries
**Redis** manages real-time queue with sorted sets

---

## 🚀 Quick Start

### 1️⃣ Prerequisites
- Python 3.9+
- Docker & Docker Compose

### 2️⃣ Installation

```bash
# Clone repository
git clone <your-repo-url>
cd Qure-Clinic-Management-System/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start databases (PostgreSQL, MongoDB, Redis)
docker-compose up -d

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://clinic_user:clinic_pass@localhost:5433/clinic_db
MONGO_URL=mongodb://clinic_admin:clinic_mongo_pass@localhost:27017/
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
EOF

# Run database migrations
alembic upgrade head

# Start the API
uvicorn app.main:app --reload
```

### 3️⃣ Access

- **API:** http://localhost:8000
- **Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 📍 API Endpoints

### Authentication
```
POST   /auth/login       # Get JWT token
POST   /auth/register    # Register user (admin only)
```

### Patients
```
GET    /patients            # List/search patients
POST   /patients            # Register new patient
GET    /patients/{id}       # Get patient details
PATCH  /patients/{id}       # Update patient
DELETE /patients/{id}       # Delete patient
```

### Appointments & Slots
```
POST   /slots/bulk          # Create appointment slots
GET    /slots               # List available slots
POST   /appointments        # Book appointment
GET    /appointments        # List appointments
PATCH  /appointments/{id}   # Update appointment
```

### Queue Management
```
POST   /queue/checkin       # Check-in with appointment
POST   /queue/walk-in       # Add walk-in patient
GET    /queue/today         # View today's queue
POST   /queue/next          # Call next patient
PATCH  /queue/{token}/status  # Update status
```

### Visits & Prescriptions
```
POST   /visits              # Start consultation
PATCH  /visits/{id}         # Record vitals/diagnosis
POST   /visits/{id}/notes   # Add clinical notes
POST   /visits/{id}/complete # Complete visit
POST   /prescriptions       # Create prescription
GET    /prescriptions/{id}/print  # Print prescription
```

### Billing
```
POST   /billing             # Generate invoice (auto/manual)
GET    /billing/{id}        # View invoice
POST   /billing/{id}/pay    # Mark as paid
```

### Pharmacy & Inventory
```
GET    /inventory/medicines        # List medicines
POST   /inventory/medicines        # Add medicine
POST   /inventory/batches          # Add stock batch
PATCH  /inventory/batches/{id}     # Update stock
GET    /inventory/low-stock        # Low stock alerts
POST   /dispensing                 # Dispense medicines (FIFO)
```

### Reports & Analytics
```
GET    /reports/audit-logs         # Audit trail (MongoDB)
GET    /reports/visit-history      # Patient visit history
GET    /reports/stock-movements    # Inventory transactions
GET    /reports/daily-summary      # Daily statistics
```

---

## 🔐 Role-Based Access Control

| Role | Access |
|------|--------|
| **ADMIN** | Full system access |
| **DOCTOR** | Patients, visits, prescriptions, queue |
| **PHARMACIST** | Inventory, dispensing, prescriptions (read) |
| **RECEPTION** | Patients, appointments, queue, billing |

---

## 💾 Data Storage Strategy

### PostgreSQL (Primary Database)
Stores all operational data:
- Users, Patients, Appointments, Slots
- Visits, Prescriptions, Medicines, Batches
- Invoices, Dispensing records

### MongoDB (Analytics & Logs)
```javascript
// audit_logs - Track all user actions
{
  timestamp: ISODate,
  user: { id, name, role },
  action: "CREATE" | "UPDATE" | "DELETE",
  resource: { type, id },
  changes: {}
}

// visit_history - Complete visit records
{
  visit_id: int,
  patient: {},
  doctor: {},
  vitals: {},
  diagnosis: "",
  prescription: [],
  visit_date: ISODate
}

// stock_movements - Inventory tracking
{
  medicine: { id, name },
  batch_number: "",
  movement_type: "IN" | "OUT" | "ADJUSTMENT",
  quantity: int,
  timestamp: ISODate
}

// daily_summaries - Aggregated stats
{
  date: ISODate,
  total_patients: int,
  total_visits: int,
  total_revenue: decimal,
  medicines_dispensed: int
}
```

### Redis (Real-Time Queue)
```redis
# Queue management keys
queue:{date}                    # Sorted set (timestamp as score)
queue:token:{date}:{number}     # Hash of patient details
queue:counter:{date}            # Auto-incrementing token number
queue:current:{date}            # Currently serving token
```

---

## 🐳 Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Access database shells
docker exec -it clinic_db psql -U clinic_user -d clinic_db
docker exec -it clinic_mongo mongosh "mongodb://clinic_admin:clinic_mongo_pass@localhost:27017/"
docker exec -it clinic_redis redis-cli
```

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── routers/          # API endpoints
│   │   ├── auth.py
│   │   ├── patients.py
│   │   ├── appointments.py
│   │   ├── visits.py
│   │   ├── prescriptions.py
│   │   ├── billing.py
│   │   ├── inventory.py
│   │   ├── dispensing.py
│   │   ├── queue.py
│   │   └── reports.py
│   ├── services/         # Business logic
│   ├── models.py         # SQLAlchemy models
│   ├── schemas.py        # Pydantic schemas
│   ├── database.py       # PostgreSQL connection
│   ├── mongo_client.py   # MongoDB connection
│   ├── redis_client.py   # Redis connection
│   ├── auth.py           # JWT authentication
│   └── main.py           # FastAPI app
├── alembic/              # Database migrations
├── requirements.txt
├── docker-compose.yml
└── .env
```

---

## 🔒 Security Features

✅ JWT-based authentication with token expiration
✅ Password hashing with bcrypt
✅ Role-based access control (RBAC)
✅ SQL injection prevention (SQLAlchemy ORM)
✅ Audit logging for all critical actions
✅ Environment variable configuration

---

## 🧪 Development

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Run tests
pytest

# Code formatting
black app/
```

---

## 📄 License

MIT License - Open source and free to use

---

## 👨‍💻 Built With

- **FastAPI** - Modern Python web framework
- **SQLAlchemy 2.0** - Async ORM
- **PostgreSQL** - Relational database
- **MongoDB** - Document store for analytics
- **Redis** - In-memory cache for queues
- **Alembic** - Database migrations
- **Pydantic** - Data validation
- **JWT** - Token-based auth

---

**⚠️ Note:** This is a production-ready system. Ensure compliance with healthcare regulations (HIPAA, GDPR) before deployment.