# 🏥 Qure Clinic Management System

A complete clinic management platform with integrated pharmacy, real-time queue management, and comprehensive analytics built with FastAPI, PostgreSQL, MongoDB, and Redis.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.5-009688.svg)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB.svg)](https://www.python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192.svg)](https://www.postgresql.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-47A248.svg)](https://www.mongodb.com)
[![Redis](https://img.shields.io/badge/Redis-7.0-DC382D.svg)](https://redis.io)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [Database Design](#-database-design)
- [API Documentation](#-api-documentation)
- [User Roles](#-user-roles)
- [Workflows](#-workflows)
- [Development](#-development)
- [Security](#-security)

---

## 🎯 Overview

Qure is an end-to-end clinic management system designed to streamline healthcare operations. It manages the complete patient journey from registration through consultation, prescription, billing, and pharmacy dispensing.

### What Problems Does It Solve?

- **Patient Management** - Centralized patient records with medical history
- **Appointment Chaos** - Slot-based scheduling prevents overbooking
- **Queue Confusion** - Token-based queue system with real-time updates
- **Paper Prescriptions** - Digital prescriptions with dosage tracking
- **Inventory Issues** - FIFO-based stock management with expiry alerts
- **Billing Errors** - Automated billing from prescriptions
- **No Audit Trail** - Comprehensive logging of all actions

### Key Highlights

✅ **Real-time Queue** - Redis-powered token system for managing patient flow
✅ **Multi-Database Architecture** - PostgreSQL for data, MongoDB for analytics, Redis for cache
✅ **Role-Based Access** - Four user roles with specific permissions
✅ **FIFO Dispensing** - Automatic batch selection based on expiry dates
✅ **Comprehensive Audit** - Every action logged with user, timestamp, and changes
✅ **Automated Billing** - Generate invoices directly from prescriptions

---

## ✨ Features

### 👥 Patient Management
- Complete patient registration with medical history
- Search by name, phone, or ID
- Track allergies and chronic conditions
- Emergency contact information
- View complete visit history

### 📅 Appointments & Scheduling
- Doctor availability slots (15/30 min intervals)
- Bulk slot creation for multiple days
- Block slots for breaks or unavailability
- Appointment booking with conflict prevention
- Walk-in patient support

### 🎫 Queue Management
- Token-based queue system
- Real-time status updates
- Priority for appointment patients
- Display current token on screens
- Queue statistics and summaries

### 🏥 Clinical Consultations
- Record vital signs (BP, temp, pulse, SpO2, weight, height)
- Chief complaints and symptoms
- Clinical notes with categories (symptom, observation, diagnosis, treatment)
- Diagnosis and treatment plans
- Complete visit history

### 💊 Prescriptions & Pharmacy
- Digital prescription creation
- Medicine dosage, frequency, and duration
- Special instructions for each medicine
- Printable prescription format
- FIFO-based dispensing (First Expiry, First Out)
- Automatic inventory deduction

### 📦 Inventory Management
- Medicine catalog with generic names
- Batch tracking with expiry dates
- Stock level monitoring
- Reorder level alerts
- Stock movement logging
- Expiry date alerts (30/60/90 days)

### 💰 Billing & Invoicing
- **AUTO Mode**: Generate bill from prescription automatically
- **MANUAL Mode**: Custom billing for procedures/tests
- Tax and discount calculations
- Multiple payment methods (Cash, Card, UPI)
- Invoice status tracking
- Receipt generation

### 📊 Analytics & Reports
- Audit logs (all user actions)
- Visit history with prescriptions
- Stock movement reports
- Daily summaries (patients, revenue, medicines dispensed)
- Top medicines and diagnoses

---

## 🏗️ System Architecture

### High-Level Architecture

```mermaid
graph TB
    Client[Client]

    subgraph Backend
        API[FastAPI]
        Auth[JWT Auth]
        Routes[Routes]
        Services[Services]
    end

    subgraph Data
        PG[(PostgreSQL)]
        Mongo[(MongoDB)]
        Redis[(Redis)]
    end

    Client --> API
    API --> Auth
    Auth --> Routes
    Routes --> Services

    Services --> PG
    Services --> Mongo
    Services --> Redis
```

### Data Flow

**PostgreSQL** handles all operational data:
- Users, Patients, Appointments, Visits
- Prescriptions, Medicines, Inventory
- Billing, Invoices, Dispensing

**MongoDB** stores analytics and logs:
- Audit logs (user actions)
- Visit history (complete records)
- Stock movements (inventory changes)
- Daily summaries (aggregated stats)

**Redis** manages real-time operations:
- Queue management (sorted sets)
- Token generation (counters)
- Current serving token (strings)
- Session cache

---

## 🛠️ Tech Stack

### Backend
- **FastAPI 0.115.5** - Modern async web framework
- **Python 3.9+** - Programming language
- **Pydantic** - Data validation and settings
- **SQLAlchemy 2.0** - Async ORM
- **Alembic** - Database migrations

### Databases
- **PostgreSQL 16** - Primary relational database
- **MongoDB 7** - Document store for analytics
- **Redis 7** - In-memory cache and queue

### Authentication & Security
- **JWT** - Token-based authentication
- **Bcrypt** - Password hashing
- **python-jose** - JWT encoding/decoding
- **passlib** - Password utilities

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **Uvicorn** - ASGI server

### Python Libraries
- **asyncpg** - Async PostgreSQL driver
- **motor** - Async MongoDB driver
- **redis-py** - Redis client
- **python-multipart** - Form data handling
- **email-validator** - Email validation

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- Docker and Docker Compose
- Git

### Installation Steps

**1. Clone the Repository**
```bash
git clone https://github.com/harshit-tew/Qure-Clinic-Management-System.git
cd Qure-Clinic-Management-System/backend
```

**2. Create Virtual Environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**3. Install Dependencies**
```bash
pip install -r requirements.txt
```

**4. Start Database Services**
```bash
docker-compose up -d
```

This starts:
- PostgreSQL on port 5433
- MongoDB on port 27017
- Redis on port 6379

**5. Create Environment File**

Create `.env` file in the `backend` directory:
```env
DATABASE_URL=postgresql+asyncpg://clinic_user:clinic_pass@localhost:5433/clinic_db
MONGO_URL=mongodb://clinic_admin:clinic_mongo_pass@localhost:27017/
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**6. Run Database Migrations**
```bash
alembic upgrade head
```

**7. Start the API**
```bash
uvicorn app.main:app --reload
```

The API will be available at: **http://localhost:8000**

### Access Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

## 💾 Database Design

### PostgreSQL Schema

**Core Tables:**
- `users` - System users (doctors, staff)
- `patients` - Patient records
- `slots` - Doctor availability slots
- `appointments` - Appointment bookings
- `visits` - Consultation records
- `clinical_notes` - Visit notes

**Prescription & Pharmacy:**
- `prescriptions` - Prescription headers
- `prescription_items` - Individual medicines
- `medicines` - Medicine catalog
- `medicine_batches` - Stock batches with expiry

**Financial:**
- `invoices` - Bills and payments
- `invoice_items` - Line items
- `dispensing` - Dispensing records
- `dispensing_items` - Medicines dispensed

### Entity Relationships

```mermaid
erDiagram
    USERS ||--o{ VISITS : conducts
    USERS ||--o{ SLOTS : has
    PATIENTS ||--o{ APPOINTMENTS : books
    PATIENTS ||--o{ VISITS : has
    SLOTS ||--o{ APPOINTMENTS : contains
    APPOINTMENTS ||--o| VISITS : becomes
    VISITS ||--|| PRESCRIPTIONS : generates
    PRESCRIPTIONS ||--o{ PRESCRIPTION_ITEMS : contains
    MEDICINES ||--o{ PRESCRIPTION_ITEMS : includes
    MEDICINES ||--o{ MEDICINE_BATCHES : has
    PRESCRIPTIONS ||--o| INVOICES : billed
    INVOICES ||--o| DISPENSING : triggers
```

### MongoDB Collections

**audit_logs**
```javascript
{
  timestamp: ISODate,
  user: { id, name, role },
  action: "CREATE|UPDATE|DELETE",
  resource: { type, id },
  changes: { old: {}, new: {} }
}
```

**visit_history**
```javascript
{
  visit_id: int,
  patient: { id, name, phone },
  doctor: { id, name },
  vitals: {},
  diagnosis: string,
  prescription: [],
  visit_date: ISODate
}
```

**stock_movements**
```javascript
{
  medicine: { id, name },
  batch_number: string,
  movement_type: "IN|OUT|ADJUSTMENT",
  quantity: int,
  timestamp: ISODate,
  performed_by: { id, name }
}
```

**daily_summaries**
```javascript
{
  date: ISODate,
  total_patients: int,
  total_visits: int,
  total_revenue: decimal,
  medicines_dispensed: int
}
```

### Redis Keys

```
queue:YYYY-MM-DD                  # Sorted set (timestamp as score)
queue:token:YYYY-MM-DD:NNN        # Hash (patient details)
queue:counter:YYYY-MM-DD          # Integer (last token number)
queue:current:YYYY-MM-DD          # String (current token)
```

---

## 📍 API Documentation

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Login and get JWT token |
| POST | `/auth/register` | Register new user (admin only) |

### Patients

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/patients` | List/search patients |
| POST | `/patients` | Register new patient |
| GET | `/patients/{id}` | Get patient details |
| PATCH | `/patients/{id}` | Update patient |
| DELETE | `/patients/{id}` | Delete patient |

### Appointments & Slots

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/slots/bulk` | Create multiple slots |
| GET | `/slots` | List available slots |
| PATCH | `/slots/{id}/block` | Block/unblock slot |
| POST | `/appointments` | Book appointment |
| GET | `/appointments` | List appointments |
| PATCH | `/appointments/{id}` | Update appointment |
| DELETE | `/appointments/{id}` | Cancel appointment |

### Queue Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/queue/checkin` | Check-in with appointment |
| POST | `/queue/walk-in` | Add walk-in patient |
| GET | `/queue/today` | Get today's queue |
| POST | `/queue/next` | Call next patient |
| PATCH | `/queue/{token}/status` | Update token status |
| GET | `/queue/today/summary` | Queue statistics |

### Visits & Consultations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/visits` | Start new visit |
| GET | `/visits/{id}` | Get visit details |
| PATCH | `/visits/{id}` | Update vitals/diagnosis |
| POST | `/visits/{id}/notes` | Add clinical note |
| GET | `/visits/{id}/notes` | Get clinical notes |
| POST | `/visits/{id}/complete` | Complete visit |

### Prescriptions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/prescriptions` | Create prescription |
| GET | `/prescriptions/{id}` | Get prescription |
| GET | `/prescriptions/{id}/print` | Printable format |

### Billing

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/billing` | Generate invoice |
| GET | `/billing/{id}` | Get invoice |
| PATCH | `/billing/{id}` | Update invoice |
| POST | `/billing/{id}/pay` | Mark as paid |

### Inventory

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/inventory/medicines` | List medicines |
| POST | `/inventory/medicines` | Add medicine |
| GET | `/inventory/low-stock` | Low stock alerts |
| POST | `/inventory/batches` | Add stock batch |
| PATCH | `/inventory/batches/{id}` | Update stock |

### Pharmacy

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/dispensing` | Dispense medicines |
| GET | `/dispensing/{id}` | Get dispensing record |

### Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/reports/audit-logs` | Audit trail |
| GET | `/reports/visit-history` | Visit history |
| GET | `/reports/stock-movements` | Stock movements |
| GET | `/reports/daily-summary` | Daily statistics |

---

## 👤 User Roles

### ADMIN
**Full system access**
- Manage users (create, update, delete)
- Access all patient records
- View all reports and analytics
- System configuration

### DOCTOR
**Clinical operations**
- View patient records
- Manage appointments and slots
- Conduct visits and add notes
- Create prescriptions
- View queue and call patients

### PHARMACIST
**Pharmacy operations**
- View prescriptions (read-only)
- Dispense medicines
- Manage inventory
- Add/update stock batches
- View stock reports

### RECEPTION
**Front desk operations**
- Register patients
- Book appointments
- Manage queue (check-in, walk-in)
- Generate invoices
- Process payments

---

## 🔄 Workflows

### Complete Patient Journey

```mermaid
graph LR
    A[Arrive] --> B[Register]
    B --> C[Check-in]
    C --> D[Queue]
    D --> E[Visit]
    E --> F[Prescription]
    F --> G[Billing]
    G --> H[Payment]
    H --> I[Dispense]
    I --> J[Complete]
```

**Step-by-step:**

1. **Registration** - Patient arrives and registers (if new) or reception searches existing record
2. **Check-in** - Patient checks in with appointment or added as walk-in
3. **Queue** - Token generated and patient joins queue (Redis)
4. **Visit** - Doctor calls next patient and starts consultation
5. **Prescription** - Doctor creates prescription with medicines
6. **Billing** - Invoice generated automatically from prescription
7. **Payment** - Patient pays via cash/card/UPI
8. **Dispensing** - Pharmacist dispenses medicines using FIFO
9. **Complete** - Patient receives medicines and receipt

### Queue Flow

```mermaid
graph TB
    A[Patient] --> B{Type?}
    B -->|Appointment| C[Check-in]
    B -->|Walk-in| D[Register]
    C --> E[Token]
    D --> E
    E --> F[Wait]
    F --> G[Called]
    G --> H[Visit]
```

### Dispensing Flow (FIFO)

```mermaid
graph LR
    A[Prescription] --> B[Check Stock]
    B --> C[Select Batch]
    C --> D[FIFO Logic]
    D --> E[Earliest Expiry]
    E --> F[Deduct Stock]
    F --> G[Log Movement]
    G --> H[Dispense]
```

**FIFO Logic:**
1. Query all batches for the medicine
2. Filter out expired batches
3. Sort by expiry date (earliest first)
4. Select batch with sufficient quantity
5. Deduct from that batch
6. If insufficient, use next batch

---

## 🔧 Development

### Project Structure

```
backend/
├── app/
│   ├── routers/              # API endpoints
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
│   ├── services/             # Business logic
│   │   ├── queue_service.py
│   │   └── mongo_services.py
│   ├── models.py             # SQLAlchemy models
│   ├── schemas.py            # Pydantic schemas
│   ├── database.py           # PostgreSQL setup
│   ├── mongo_client.py       # MongoDB setup
│   ├── redis_client.py       # Redis setup
│   ├── auth.py               # JWT authentication
│   ├── config.py             # Configuration
│   └── main.py               # FastAPI app
├── alembic/                  # Database migrations
├── requirements.txt
├── docker-compose.yml
└── .env
```

### Database Migrations

**Create migration:**
```bash
alembic revision --autogenerate -m "add new table"
```

**Apply migrations:**
```bash
alembic upgrade head
```

**Rollback:**
```bash
alembic downgrade -1
```

### Docker Commands

**Start services:**
```bash
docker-compose up -d
```

**View logs:**
```bash
docker-compose logs -f
docker logs clinic_db
docker logs clinic_mongo
docker logs clinic_redis
```

**Stop services:**
```bash
docker-compose down
```

**Access database shells:**
```bash
# PostgreSQL
docker exec -it clinic_db psql -U clinic_user -d clinic_db

# MongoDB
docker exec -it clinic_mongo mongosh "mongodb://clinic_admin:clinic_mongo_pass@localhost:27017/"

# Redis
docker exec -it clinic_redis redis-cli
```

### Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app tests/
```

### Code Quality

```bash
# Format code
black app/

# Sort imports
isort app/

# Lint
flake8 app/
```

---

## 🔒 Security

### Authentication
- JWT token-based authentication
- Token expiration (30 minutes default)
- Secure password hashing with bcrypt
- Password validation (minimum length, complexity)

### Authorization
- Role-based access control (RBAC)
- Endpoint-level permission checks
- User context from JWT token

### Data Protection
- SQL injection prevention (SQLAlchemy ORM)
- Input validation (Pydantic)
- Environment variable configuration
- Sensitive data never logged

### Audit Trail
- All actions logged to MongoDB
- User, timestamp, and changes recorded
- IP address tracking
- Immutable audit logs

### Best Practices
- HTTPS in production
- CORS middleware configured
- Rate limiting (implement as needed)
- Regular security audits
- Dependency updates

---

## 📊 Key Features Deep Dive

### Real-Time Queue System

The queue system uses Redis for high performance:

**Data Structure:**
- Sorted Set: Maintains queue order by timestamp
- Hash: Stores patient details for each token
- Counter: Generates unique token numbers
- String: Tracks currently serving token

**Operations:**
- O(log N) for adding to queue
- O(1) for getting next patient
- O(1) for updating status

**Benefits:**
- Real-time updates
- No database locking
- Fast token generation
- Persistent across restarts

### FIFO Dispensing

Medicine dispensing follows First-In-First-Out (FIFO) or more accurately, First-Expiry-First-Out:

**Logic:**
1. Query all batches for medicine
2. Filter expired batches
3. Sort by expiry date ascending
4. Select batch with earliest expiry
5. Deduct quantity
6. Log movement to MongoDB

**Benefits:**
- Reduces medicine wastage
- Prevents dispensing expired medicines
- Automatic stock rotation
- Complete audit trail

### Automated Billing

**AUTO Mode:**
1. Fetch prescription details
2. Get medicine prices from inventory
3. Calculate subtotal (quantity × price)
4. Apply discounts if any
5. Calculate tax (18% GST)
6. Generate invoice

**MANUAL Mode:**
1. Add custom line items
2. Enter consultation fee
3. Add procedure charges
4. Calculate totals
5. Generate invoice

### Audit Logging

Every significant action is logged:
- User who performed action
- Timestamp
- Resource affected (type and ID)
- Changes made (old → new values)
- Result (success/failure)

**Use cases:**
- Compliance requirements
- Security monitoring
- Debugging
- Performance analysis
- Business intelligence

---

## 🐳 Docker Setup

### docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: clinic_db
    environment:
      POSTGRES_USER: clinic_user
      POSTGRES_PASSWORD: clinic_pass
      POSTGRES_DB: clinic_db
    ports:
      - "5433:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  mongodb:
    image: mongo:7
    container_name: clinic_mongo
    environment:
      MONGO_INITDB_ROOT_USERNAME: clinic_admin
      MONGO_INITDB_ROOT_PASSWORD: clinic_mongo_pass
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  redis:
    image: redis:7-alpine
    container_name: clinic_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  mongo_data:
  redis_data:
```

---

## 📈 Performance Considerations

### Database Indexes

**PostgreSQL:**
- Primary keys on all tables
- Foreign key indexes
- Search indexes (patient name, phone)
- Date indexes (appointments, visits)

**MongoDB:**
- Timestamp indexes (audit_logs)
- Patient ID + date (visit_history)
- Medicine ID + timestamp (stock_movements)
- Date unique index (daily_summaries)

### Caching Strategy

- Redis for queue management
- Session caching
- Frequently accessed data
- API response caching (future)

### Query Optimization

- Async database operations
- Bulk inserts where possible
- JOIN optimization
- Pagination for large result sets

---

## 🚧 Roadmap

### Planned Features
- [ ] SMS notifications for appointments
- [ ] Email prescriptions to patients
- [ ] Mobile app for doctors
- [ ] Lab integration
- [ ] Imaging integration (X-ray, MRI)
- [ ] Telemedicine support
- [ ] Patient portal
- [ ] Insurance claims
- [ ] Multi-clinic support
- [ ] Analytics dashboard

---

## 📄 License

MIT License - Free to use, modify, and distribute.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 👨‍💻 Support

For questions or issues:
- Open an issue on GitHub
- Email: support@qure-clinic.example

---

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [PostgreSQL](https://www.postgresql.org/) - Powerful relational database
- [MongoDB](https://www.mongodb.com/) - Flexible document database
- [Redis](https://redis.io/) - In-memory data store
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit and ORM
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation

---

**⚠️ Important:** This system handles sensitive health data. Ensure compliance with healthcare regulations (HIPAA, GDPR, HITECH) before deployment in production. Implement proper backup strategies, access controls, and encryption.

---

**Made with ❤️ for better healthcare management**