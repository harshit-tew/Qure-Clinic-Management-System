# Qure Clinic Management System

A complete clinic management platform with integrated pharmacy, real-time queue management, and comprehensive analytics built with FastAPI, PostgreSQL, MongoDB, and Redis.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.5-009688.svg)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB.svg)](https://www.python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192.svg)](https://www.postgresql.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-47A248.svg)](https://www.mongodb.com)
[![Redis](https://img.shields.io/badge/Redis-7.0-DC382D.svg)](https://redis.io)

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Database Design](#database-design)
- [API Documentation](#api-documentation)
- [User Roles](#user-roles)
- [Workflows](#workflows)
- [Development](#development)
- [Security](#security)

---

## Overview

Qure is an end-to-end clinic management system designed to streamline healthcare operations. It manages the complete patient journey from registration through consultation, prescription, billing, and pharmacy dispensing — all in a single connected system.

### What Problems Does It Solve?

- **Patient Management** — Centralized patient records with full medical history
- **Appointment Chaos** — Slot-based scheduling prevents double-booking
- **Queue Confusion** — Token-based queue system with real-time updates via Redis
- **Paper Prescriptions** — Digital prescriptions with dosage tracking
- **Inventory Issues** — FIFO-based stock management with expiry alerts
- **Billing Errors** — Automated billing generated directly from prescriptions
- **No Audit Trail** — Every action logged with user, timestamp, and changes

---

## How It Works

This section explains the full flow of the system in plain terms — from when a patient walks in to when they leave.

### The Patient Journey at a Glance

```
Patient Arrives
      |
      +--> New Patient? ---> Register (name, DOB, phone, allergies, etc.)
      |
      +--> Existing? ------> Search by name / phone / ID
      |
      v
Check-in at Reception
      |
      +--> Has Appointment? ---> Check-in against appointment slot
      |
      +--> Walk-in? -----------> Added directly to queue
      |
      v
Token Issued (Redis Queue)
      |
      v
Patient Waits --> Doctor Calls Next Token
      |
      v
Consultation Begins
      |
      +--> Vitals recorded (BP, temp, pulse, SpO2, weight, height)
      +--> Chief complaint noted
      +--> Clinical notes added (symptoms, observations, diagnosis, treatment)
      +--> Diagnosis and treatment plan saved
      |
      v
Prescription Created (if medicines needed)
      |
      v
Visit Marked Complete --> Full record saved to MongoDB
      |
      v
Invoice Generated
      |
      +--> AUTO mode: pulls medicine prices from prescription automatically
      +--> MANUAL mode: reception adds consultation fee + custom charges
      |
      v
Patient Pays (Cash / Card / UPI)
      |
      v
Pharmacist Dispenses Medicines (FIFO — earliest expiry batch first)
      |
      v
Stock Deducted --> Movement logged to MongoDB --> Low-stock alert if needed
      |
      v
Patient Receives Medicines + Receipt --> Journey Complete
```

### Three Databases, Three Purposes

The system uses three databases, each chosen for what it does best:

**PostgreSQL** is the source of truth for all operational data. Every patient, appointment, visit, prescription, invoice, and stock batch lives here. It handles transactions, enforces foreign keys, and ensures data consistency.

**MongoDB** handles analytics and audit logs. When a visit completes, a full snapshot is written to `visit_history`. Every user action (create, update, delete, payment) is logged to `audit_logs`. Stock movements are recorded in `stock_movements`. At end of day, totals are aggregated into `daily_summaries`. MongoDB's flexible schema makes it ideal for these varied, write-heavy records.

**Redis** powers the real-time queue. When a patient checks in, a token is minted using an atomic counter (`INCR`), stored in a sorted set (`ZADD`) ordered by check-in time, and their details saved in a hash. When the doctor calls the next patient, Redis returns the first token in O(1) time. The currently-serving token is stored as a plain string key. This keeps the queue fast and free of database load.

### Role-Based Access

Four roles control what each user can do:

| Role | Responsible for |
|------|----------------|
| **Admin** | User management, full system access, all reports |
| **Doctor** | Appointments, consultations, prescriptions, calling queue |
| **Pharmacist** | Inventory, dispensing, stock batches |
| **Reception** | Patient registration, check-in, queue management, billing |

Each API endpoint checks the JWT token's role before allowing access. A pharmacist cannot create a prescription; a doctor cannot dispense medicines.

### Authentication

Every request requires a JWT bearer token. Logging in returns a token valid for 30 minutes. The token contains the user's ID and role, which the API reads on every request — no extra database round-trip needed to check permissions.

---

## Features

### Patient Management
- Complete patient registration with medical history
- Search by name, phone, or ID
- Track allergies and chronic conditions
- Emergency contact information
- View complete visit history

### Appointments & Scheduling
- Doctor availability slots (15/30 min intervals)
- Bulk slot creation for multiple days
- Block slots for breaks or unavailability
- Appointment booking with conflict prevention
- Walk-in patient support

### Queue Management
- Token-based queue system backed by Redis
- Real-time status updates (WAITING → WITH_DOCTOR → COMPLETED)
- Priority for appointment patients over walk-ins
- Display current token for screens
- Queue statistics and daily summaries

### Clinical Consultations
- Record vital signs (BP, temperature, pulse, SpO2, weight, height)
- Chief complaints and symptom duration
- Clinical notes with categories: SYMPTOM, OBSERVATION, DIAGNOSIS, TREATMENT
- Diagnosis and treatment plans
- Complete visit history stored in MongoDB

### Prescriptions & Pharmacy
- Digital prescription creation linked to the visit
- Medicine dosage, frequency, duration, and special instructions
- Printable prescription format
- FIFO-based dispensing (earliest expiry first)
- Automatic inventory deduction on dispensing

### Inventory Management
- Medicine catalog with generic names and dosage forms
- Batch tracking with expiry dates and supplier info
- Stock level monitoring with reorder alerts
- Stock movement logging (IN / OUT / ADJUSTMENT)
- Expiry alerts at 30, 60, and 90 days

### Billing & Invoicing
- **AUTO mode** — invoice generated directly from prescription line items
- **MANUAL mode** — custom billing for procedures, tests, consultation fees
- Tax (GST) and discount calculations
- Multiple payment methods: Cash, Card, UPI
- Invoice status: DRAFT → PENDING → PAID

### Analytics & Reports
- Audit logs (all user actions with before/after values)
- Visit history with full prescription snapshots
- Stock movement reports
- Daily summaries: patients seen, revenue, medicines dispensed

---

## System Architecture

```
                        ┌─────────────────────────┐
                        │      Client Layer        │
                        │  Web  |  Mobile  | Admin │
                        └──────────┬──────────────┘
                                   │ HTTP requests
                                   v
                        ┌─────────────────────────┐
                        │      FastAPI App         │
                        │                         │
                        │  JWT Auth Middleware     │
                        │         │               │
                        │         v               │
                        │    API Routers          │
                        │  auth | patients |      │
                        │  appointments | visits  │
                        │  prescriptions | billing│
                        │  inventory | queue |    │
                        │  reports               │
                        │         │               │
                        │         v               │
                        │  Business Logic /       │
                        │  Services               │
                        └────┬─────────┬──────┬───┘
                             │         │      │
                    ┌────────▼──┐ ┌────▼───┐ ┌▼──────┐
                    │PostgreSQL │ │MongoDB │ │ Redis │
                    │Operational│ │Analytics│ │Queue  │
                    │  Data     │ │& Logs  │ │&Cache │
                    └───────────┘ └────────┘ └───────┘
```

### What Each Database Stores

**PostgreSQL** (primary relational store):
- `users`, `patients`, `slots`, `appointments`, `visits`, `clinical_notes`
- `prescriptions`, `prescription_items`, `medicines`, `medicine_batches`
- `invoices`, `invoice_items`, `dispensing`, `dispensing_items`

**MongoDB** (analytics and audit):
- `audit_logs` — every user action with old/new values
- `visit_history` — complete visit snapshots including vitals and prescriptions
- `stock_movements` — every stock IN/OUT with batch details
- `daily_summaries` — aggregated daily stats for dashboards

**Redis** (real-time queue):
```
queue:YYYY-MM-DD            → Sorted set  (tokens ordered by check-in time)
queue:token:YYYY-MM-DD:NNN  → Hash        (patient info, status, timestamps)
queue:counter:YYYY-MM-DD    → Integer     (auto-incrementing token number)
queue:current:YYYY-MM-DD    → String      (token currently being seen)
```

---

## Tech Stack

### Backend
- **FastAPI 0.115.5** — Modern async web framework
- **Python 3.9+** — Programming language
- **Pydantic** — Data validation and settings management
- **SQLAlchemy 2.0** — Async ORM
- **Alembic** — Database migrations

### Databases
- **PostgreSQL 16** — Primary relational database
- **MongoDB 7** — Document store for analytics and logs
- **Redis 7** — In-memory cache and queue

### Authentication & Security
- **JWT** — Token-based authentication
- **Bcrypt** — Password hashing
- **python-jose** — JWT encoding/decoding
- **passlib** — Password utilities

### Infrastructure
- **Docker** — Containerization
- **Docker Compose** — Multi-container orchestration
- **Uvicorn** — ASGI server

### Python Libraries
- **asyncpg** — Async PostgreSQL driver
- **motor** — Async MongoDB driver
- **redis-py** — Redis client
- **python-multipart** — Form data handling
- **email-validator** — Email validation

---

## Quick Start

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

Create `.env` in the `backend` directory:
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

## Database Design

### PostgreSQL Schema

**Core Tables:**
- `users` — System users (doctors, staff, admin, pharmacist, reception)
- `patients` — Patient records with allergies and emergency contacts
- `slots` — Doctor availability slots (15/30 min intervals)
- `appointments` — Appointment bookings linked to a slot and patient

**Clinical:**
- `visits` — Consultation records with vitals, diagnosis, treatment plan
- `clinical_notes` — Per-visit notes (SYMPTOM / OBSERVATION / DIAGNOSIS / TREATMENT)

**Prescription & Pharmacy:**
- `prescriptions` — Prescription header linked to visit
- `prescription_items` — Individual medicines with dosage, frequency, duration
- `medicines` — Medicine catalog with pricing and reorder levels
- `medicine_batches` — Stock batches with expiry dates and quantities

**Financial:**
- `invoices` — Bills with subtotal, discount, tax, payment method
- `invoice_items` — Line items on each invoice
- `dispensing` — Dispensing records per prescription
- `dispensing_items` — Per-medicine batch deductions

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
```json
{
  "timestamp": "ISODate",
  "user": { "id": 1, "name": "Dr. Smith", "role": "DOCTOR" },
  "action": "VISIT_COMPLETED",
  "resource": { "type": "visit", "id": 42 },
  "changes": { "old": {}, "new": {} }
}
```

**visit_history**
```json
{
  "visit_id": 42,
  "patient": { "id": 1, "name": "John Doe", "phone": "9999999999" },
  "doctor": { "id": 2, "name": "Dr. Smith" },
  "vitals": { "bp": "120/80", "temp": "98.6", "pulse": 72 },
  "diagnosis": "Viral URTI",
  "prescription": [],
  "visit_date": "ISODate"
}
```

**stock_movements**
```json
{
  "medicine": { "id": 5, "name": "Paracetamol 500mg" },
  "batch_number": "ABC123",
  "movement_type": "OUT",
  "quantity": 10,
  "timestamp": "ISODate",
  "performed_by": { "id": 3, "name": "Pharmacist Riya" }
}
```

**daily_summaries**
```json
{
  "date": "ISODate",
  "total_patients": 45,
  "total_visits": 43,
  "total_revenue": 18500.00,
  "medicines_dispensed": 210
}
```

---

## API Documentation

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
| PATCH | `/slots/{id}/block` | Block/unblock a slot |
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

## User Roles

### ADMIN
Full system access:
- Manage users (create, update, deactivate)
- Access all patient records and reports
- View all audit logs and analytics
- System-wide configuration

### DOCTOR
Clinical operations:
- View patient records and history
- Manage their own appointment slots
- Conduct visits, record vitals and notes
- Create and view prescriptions
- Call patients from queue

### PHARMACIST
Pharmacy operations:
- View prescriptions (read-only)
- Dispense medicines against a paid invoice
- Manage medicine catalog and stock batches
- View stock reports and movements

### RECEPTION
Front desk operations:
- Register new patients and update records
- Book and cancel appointments
- Manage queue (check-in, walk-ins)
- Generate invoices and process payments

---

## Workflows

### Patient Journey

```
Patient Arrives
    |
    +-[New]--------> POST /patients  (register with name, DOB, phone, allergies)
    |                     |
    +-[Returning]--> GET /patients?search=...
                          |
                          v
                    Has Appointment?
                    |              |
                   Yes             No
                    |              |
          POST /queue/checkin   POST /queue/walk-in
                    \              /
                     v            v
               Token issued (Redis INCR + ZADD)
                          |
                          v
               Patient waits in queue
                          |
                          v
               POST /queue/next  (doctor calls)
                          |
                    status: WITH_DOCTOR
                          |
                          v
               POST /visits  (create visit record)
                    |
                    +--> PATCH /visits/{id}  (record vitals: BP, temp, pulse, SpO2...)
                    +--> PATCH /visits/{id}  (chief complaint)
                    +--> POST /visits/{id}/notes  (clinical notes)
                    +--> PATCH /visits/{id}  (diagnosis + treatment plan)
                    |
                    v
               POST /prescriptions  (add medicines with dosage/frequency/duration)
                    |
               POST /visits/{id}/complete
                    |
               (visit snapshot saved to MongoDB)
                    |
                    v
               POST /billing
                    |
                    +-[AUTO]-----> pulls medicine prices from prescription
                    +-[MANUAL]---> reception adds custom line items
                    |
                    v
               Apply discount + 18% tax --> Total calculated
                    |
               POST /billing/{id}/pay  (Cash / Card / UPI)
                    |
                    v
               POST /dispensing  (pharmacist role required)
                    |
               FIFO batch selection --> stock deducted --> movement logged
                    |
                    v
               Patient receives medicines + receipt
               Token marked COMPLETED, removed from Redis queue
```

---

### Queue Internals (Redis)

```
Check-in / Walk-in
      |
      v
INCR queue:counter:YYYY-MM-DD        --> token number (001, 002, ...)
ZADD queue:YYYY-MM-DD score=now      --> add token to sorted set
HSET queue:token:YYYY-MM-DD:NNN      --> store patient details + status=WAITING
      |
      v
Queue Display (GET /queue/today)
Shows: waiting | with_doctor | completed | skipped
      |
      v
Doctor: POST /queue/next
      |
ZRANGE queue:date 0 0                --> get next token
HSET ...status = WITH_DOCTOR
SET queue:current:date = token_num   --> update display screen
      |
      v
Consultation completes
      |
HSET ...status = COMPLETED
ZREM queue:date token                --> remove from active queue
```

---

### FIFO Dispensing Logic

When a pharmacist dispenses medicines, the system selects stock batches in FIFO order (first to expire is dispensed first):

```
For each medicine in the prescription:
      |
      v
SELECT batches WHERE medicine_id = X
  AND quantity > 0
  AND expiry_date > TODAY
  ORDER BY expiry_date ASC          --> earliest expiry first
      |
      v
Required quantity = dose × frequency × duration_days
      |
      v
Enough in one batch?
      |              |
     Yes             No
      |              |
 Deduct all     Deduct from batch 1, carry remainder to next batch
      |
      v
UPDATE medicine_batches SET quantity = quantity - dispensed
INSERT stock_movements (type: OUT) into MongoDB
      |
      v
Stock < reorder_level?  -->  GET /inventory/low-stock alert generated
```

---

### Billing Modes

**AUTO mode** — used when a prescription exists:
```
Fetch prescription_items joined with medicines
    --> for each item: unit_price × quantity = line total
    --> sum all lines = subtotal
    --> subtotal - discount + (subtotal × 0.18 tax) = total
```

**MANUAL mode** — used for custom charges:
```
Reception adds line items manually:
    - Consultation fee
    - Procedure charges
    - Lab or imaging fees
    --> same discount + tax calculation
    --> total calculated and invoice created
```

---

## Development

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

```bash
# Create a new migration
alembic revision --autogenerate -m "add new table"

# Apply all migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

### Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
docker logs clinic_db
docker logs clinic_mongo
docker logs clinic_redis

# Stop services
docker-compose down

# Access database shells
docker exec -it clinic_db psql -U clinic_user -d clinic_db
docker exec -it clinic_mongo mongosh "mongodb://clinic_admin:clinic_mongo_pass@localhost:27017/"
docker exec -it clinic_redis redis-cli
```

### Docker Compose Reference

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: clinic_db
    ports:
      - "5433:5432"

  mongodb:
    image: mongo:7
    container_name: clinic_mongo
    ports:
      - "27017:27017"

  redis:
    image: redis:7-alpine
    container_name: clinic_redis
    ports:
      - "6379:6379"
```

### Testing

```bash
pytest
pytest --cov=app tests/
```

### Code Quality

```bash
black app/       # format
isort app/       # sort imports
flake8 app/      # lint
```

---

## Security

### Authentication & Authorization
- JWT bearer token required on all protected endpoints
- Token expiry: 30 minutes (configurable via env)
- Passwords hashed with bcrypt — never stored in plaintext
- Role-based access checked at the endpoint level using the JWT payload

### Data Protection
- SQLAlchemy ORM prevents SQL injection
- All inputs validated by Pydantic before hitting business logic
- Sensitive config (DB passwords, secret keys) stored in `.env`, never hardcoded
- Sensitive data is never written to application logs

### Audit Trail
- Every create/update/delete action writes to MongoDB `audit_logs`
- Logs include: user ID + name + role, timestamp, resource type + ID, before/after values
- Audit logs are append-only — no update or delete endpoints exposed

### Production Checklist
- Change `SECRET_KEY` to a strong random value
- Enable HTTPS (reverse proxy via nginx or a cloud load balancer)
- Restrict CORS origins to your frontend domain
- Set up regular database backups
- Ensure compliance with applicable healthcare data regulations (HIPAA, GDPR, etc.)

---

## Roadmap

- [ ] SMS/email notifications for appointment reminders
- [ ] Email prescriptions directly to patients
- [ ] Patient portal (self-service booking and history)
- [ ] Lab integration (send test orders, receive results)
- [ ] Analytics dashboard (charts for revenue, visit trends, top diagnoses)
- [ ] Multi-clinic support
- [ ] Insurance claims processing
- [ ] Mobile app for doctors

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Push and open a Pull Request

---

## License

MIT License — free to use, modify, and distribute.

---

> **Note:** This system handles sensitive health data. Ensure compliance with applicable healthcare regulations before deploying to production. Implement proper backup strategies, access controls, and encryption at rest.