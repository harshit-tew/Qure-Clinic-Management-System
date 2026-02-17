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

## 📊 System Architecture & Data Flow

### 🏗️ Overall System Architecture

```mermaid
flowchart TB
    Client[Client Application]

    subgraph FastAPI["FastAPI Backend"]
        Auth[Authentication Layer<br/>JWT Verification]
        Router[API Routers]
        Services[Business Logic Services]
    end

    subgraph Databases["Data Storage Layer"]
        PG[(PostgreSQL<br/>Relational Data)]
        Mongo[(MongoDB<br/>Logs & Analytics)]
        Redis[(Redis<br/>Queue & Cache)]
    end

    Client -->|HTTP/HTTPS| Auth
    Auth -->|Valid Token| Router
    Router --> Services

    Services -->|CRUD Operations| PG
    Services -->|Audit Logs| Mongo
    Services -->|Visit History| Mongo
    Services -->|Stock Movements| Mongo
    Services -->|Queue Management| Redis

    PG -->|Patients, Appointments<br/>Visits, Prescriptions<br/>Inventory, Billing| Services
    Mongo -->|Analytics<br/>Reports| Services
    Redis -->|Real-time Queue<br/>Status| Services

    style FastAPI fill:#e1f5ff
    style Databases fill:#fff3e0
    style Client fill:#f3e5f5
```

### 🔐 Authentication Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant API as FastAPI
    participant Auth as Auth Service
    participant PG as PostgreSQL

    C->>API: POST /auth/login<br/>(username, password)
    API->>Auth: Validate credentials
    Auth->>PG: Query user by username
    PG-->>Auth: User data
    Auth->>Auth: Verify password hash (bcrypt)

    alt Valid Credentials
        Auth->>Auth: Generate JWT Token
        Auth-->>API: Access Token + User Info
        API-->>C: 200 OK<br/>{access_token, user}
        C->>API: Subsequent requests<br/>Header: Authorization: Bearer {token}
        API->>Auth: Verify JWT token
        Auth->>Auth: Check expiration & signature
        Auth-->>API: User context
        API->>API: Check role permissions
        API-->>C: Protected resource
    else Invalid Credentials
        Auth-->>API: Authentication failed
        API-->>C: 401 Unauthorized
    end
```

### 👥 Complete Patient Journey Flow

```mermaid
flowchart TD
    Start([Patient Arrival])

    Start --> CheckReg{Registered<br/>Patient?}

    CheckReg -->|No| RegPatient[POST /patients<br/>Register New Patient]
    CheckReg -->|Yes| SearchPatient[GET /patients?search<br/>Find Patient]

    RegPatient --> PG1[(PostgreSQL<br/>Save Patient)]
    SearchPatient --> PG1

    PG1 --> CheckAppt{Has<br/>Appointment?}

    CheckAppt -->|No| WalkIn[POST /queue/walk-in<br/>Add to Queue]
    CheckAppt -->|Yes| CheckIn[POST /queue/checkin<br/>Check-in with Appointment]

    WalkIn --> Redis1[(Redis<br/>Queue Management)]
    CheckIn --> Redis1

    Redis1 --> Queue[GET /queue/today<br/>View Queue Status]
    Queue --> CallNext[POST /queue/next<br/>Call Next Patient]

    CallNext --> StartVisit[POST /visits<br/>Start Consultation]
    StartVisit --> PG2[(PostgreSQL<br/>Visit Record)]

    PG2 --> RecordVitals[PATCH /visits/{id}<br/>Record Vitals & Notes]
    RecordVitals --> AddNotes[POST /visits/{id}/notes<br/>Clinical Notes]

    AddNotes --> CreatePrescription[POST /prescriptions<br/>Create Prescription]
    CreatePrescription --> PG3[(PostgreSQL<br/>Prescription)]

    PG3 --> CompleteVisit[POST /visits/{id}/complete<br/>Complete Visit]
    CompleteVisit --> Mongo1[(MongoDB<br/>Visit History)]

    Mongo1 --> GenerateBill[POST /billing<br/>Generate Invoice]
    GenerateBill --> PG4[(PostgreSQL<br/>Invoice)]

    PG4 --> Payment[POST /billing/{id}/pay<br/>Process Payment]

    Payment --> CheckDispense{Medicines<br/>Prescribed?}

    CheckDispense -->|Yes| Dispense[POST /dispensing<br/>Dispense Medicines]
    CheckDispense -->|No| End

    Dispense --> UpdateStock[PATCH /inventory/batches<br/>Update Stock FIFO]
    UpdateStock --> PG5[(PostgreSQL<br/>Inventory)]
    UpdateStock --> Mongo2[(MongoDB<br/>Stock Movement)]

    PG5 --> End([Process Complete])
    Mongo2 --> End

    style Start fill:#4caf50,color:#fff
    style End fill:#2196f3,color:#fff
    style PG1 fill:#ff9800
    style PG2 fill:#ff9800
    style PG3 fill:#ff9800
    style PG4 fill:#ff9800
    style PG5 fill:#ff9800
    style Redis1 fill:#e91e63
    style Mongo1 fill:#00bcd4
    style Mongo2 fill:#00bcd4
```

### 📅 Appointment & Queue Management Flow

```mermaid
flowchart LR
    subgraph Admin["Admin/Doctor"]
        CreateSlots[POST /slots/bulk<br/>Create Appointment Slots]
        BlockSlot[PATCH /slots/{id}/block<br/>Block Unavailable Slots]
    end

    subgraph Reception["Reception"]
        BookAppt[POST /appointments<br/>Book Appointment]
        CheckInAppt[POST /queue/checkin<br/>Check-in Patient]
        AddWalkIn[POST /queue/walk-in<br/>Add Walk-in]
        ViewQueue[GET /queue/today<br/>Monitor Queue]
    end

    subgraph Doctor["Doctor"]
        CallNext[POST /queue/next<br/>Call Next Patient]
        UpdateStatus[PATCH /queue/{token}/status<br/>Update Patient Status]
    end

    CreateSlots --> PG1[(PostgreSQL<br/>Slots Table)]
    BlockSlot --> PG1

    PG1 --> BookAppt
    BookAppt --> PG2[(PostgreSQL<br/>Appointments)]

    PG2 --> CheckInAppt
    CheckInAppt --> Redis1[(Redis<br/>Queue: Sorted Set<br/>Token Details)]

    AddWalkIn --> Redis1

    Redis1 --> ViewQueue
    ViewQueue --> CallNext
    CallNext --> UpdateStatus

    UpdateStatus --> Redis1

    style PG1 fill:#ff9800
    style PG2 fill:#ff9800
    style Redis1 fill:#e91e63
```

### 💊 Prescription & Dispensing Flow

```mermaid
flowchart TD
    Doctor[Doctor Creates Prescription]

    Doctor --> CreatePx[POST /prescriptions<br/>Medicine Details + Dosage]
    CreatePx --> PG1[(PostgreSQL<br/>Prescriptions Table)]

    PG1 --> ViewPx[GET /prescriptions/{id}<br/>View Prescription]
    ViewPx --> PrintPx[GET /prescriptions/{id}/print<br/>Print Format]

    PrintPx --> Pharmacist{Pharmacist<br/>Reviews}

    Pharmacist --> Dispense[POST /dispensing<br/>Dispense Medicines]

    Dispense --> CheckStock[GET /inventory/medicines<br/>Check Stock Availability]
    CheckStock --> PG2[(PostgreSQL<br/>Medicine Batches)]

    PG2 --> FIFOLogic[Business Logic:<br/>FIFO - First Expiry First Out]

    FIFOLogic --> DeductStock[PATCH /inventory/batches/{id}<br/>Deduct Stock from Batch]

    DeductStock --> PG3[(PostgreSQL<br/>Update Batch Quantity)]
    DeductStock --> Mongo1[(MongoDB<br/>Log Stock Movement)]

    PG3 --> CheckLowStock{Stock Below<br/>Reorder Level?}

    CheckLowStock -->|Yes| Alert[GET /inventory/low-stock<br/>Generate Alert]
    CheckLowStock -->|No| Complete

    Alert --> Complete([Dispensing Complete])

    Mongo1 --> Analytics[Reports Service<br/>Stock Analytics]

    style Doctor fill:#4caf50,color:#fff
    style Complete fill:#2196f3,color:#fff
    style PG1 fill:#ff9800
    style PG2 fill:#ff9800
    style PG3 fill:#ff9800
    style Mongo1 fill:#00bcd4
```

### 💰 Billing Flow (Auto & Manual Modes)

```mermaid
flowchart TD
    Start{Billing Mode?}

    Start -->|Auto Mode| AutoBill[POST /billing<br/>mode: AUTO<br/>prescription_id]
    Start -->|Manual Mode| ManualBill[POST /billing<br/>mode: MANUAL<br/>custom line items]

    AutoBill --> FetchPx[Fetch Prescription Details]
    FetchPx --> PG1[(PostgreSQL<br/>Prescriptions)]

    PG1 --> CalcAuto[Calculate Total<br/>from Medicine Prices]

    ManualBill --> CalcManual[Calculate Total<br/>from Line Items]

    CalcAuto --> ApplyCalc[Apply Tax & Discounts]
    CalcManual --> ApplyCalc

    ApplyCalc --> CreateInvoice[Create Invoice Record]
    CreateInvoice --> PG2[(PostgreSQL<br/>Invoices Table<br/>Status: PENDING)]

    PG2 --> ViewInvoice[GET /billing/{id}<br/>View Invoice]

    ViewInvoice --> ProcessPayment{Payment<br/>Received?}

    ProcessPayment -->|Yes| PayInvoice[POST /billing/{id}/pay<br/>payment_method]
    ProcessPayment -->|No| WaitPayment[Status: PENDING]

    PayInvoice --> UpdateStatus[Update Invoice<br/>Status: PAID<br/>paid_at: timestamp]

    UpdateStatus --> PG3[(PostgreSQL<br/>Update Invoice)]
    UpdateStatus --> Mongo1[(MongoDB<br/>Audit Log)]

    PG3 --> PrintReceipt[Generate Receipt]
    Mongo1 --> DailySummary[Update Daily Summary]

    PrintReceipt --> End([Billing Complete])
    DailySummary --> End

    style Start fill:#9c27b0,color:#fff
    style End fill:#2196f3,color:#fff
    style PG1 fill:#ff9800
    style PG2 fill:#ff9800
    style PG3 fill:#ff9800
    style Mongo1 fill:#00bcd4
```

### 📊 MongoDB Analytics & Logging Flow

```mermaid
flowchart LR
    subgraph Events["System Events"]
        E1[User Actions<br/>CREATE/UPDATE/DELETE]
        E2[Visit Completed]
        E3[Stock Movement]
        E4[Daily Rollup]
    end

    subgraph MongoCollections["MongoDB Collections"]
        AL[(audit_logs<br/>Indexed by:<br/>- timestamp<br/>- user.id<br/>- resource.type)]

        VH[(visit_history<br/>Indexed by:<br/>- patient.id<br/>- visit_date<br/>- visit_id unique)]

        SM[(stock_movements<br/>Indexed by:<br/>- medicine.id<br/>- timestamp<br/>- movement_type)]

        DS[(daily_summaries<br/>Indexed by:<br/>- date unique)]
    end

    subgraph Reports["Reports API"]
        R1[GET /reports/audit-logs]
        R2[GET /reports/visit-history]
        R3[GET /reports/stock-movements]
        R4[GET /reports/daily-summary]
    end

    E1 -->|Log every action| AL
    E2 -->|Store complete visit| VH
    E3 -->|Track inventory change| SM
    E4 -->|Aggregate stats| DS

    AL --> R1
    VH --> R2
    SM --> R3
    DS --> R4

    R1 --> Analytics[Analytics Dashboard]
    R2 --> Analytics
    R3 --> Analytics
    R4 --> Analytics

    style AL fill:#00bcd4
    style VH fill:#00bcd4
    style SM fill:#00bcd4
    style DS fill:#00bcd4
```

### 🔄 Redis Queue Real-Time Operations

```mermaid
flowchart TD
    subgraph QueueOps["Queue Operations"]
        CheckIn[Check-in Patient<br/>POST /queue/checkin]
        WalkIn[Walk-in Patient<br/>POST /queue/walk-in]
    end

    CheckIn --> Token[Generate Token<br/>Format: date-number]
    WalkIn --> Token

    Token --> Redis1{Redis Operations}

    Redis1 -->|INCR| Counter[queue:counter:2026-02-17<br/>Increment counter]
    Redis1 -->|ZADD| SortedSet[queue:2026-02-17<br/>Add to sorted set<br/>Score: timestamp]
    Redis1 -->|HSET| TokenData[queue:token:2026-02-17:001<br/>Store patient details<br/>status: WAITING]

    Counter --> Display[Display on Screen]
    SortedSet --> Display
    TokenData --> Display

    Display --> Monitor[Reception Monitors<br/>GET /queue/today]

    Monitor --> CallNext[Doctor Calls Next<br/>POST /queue/next]

    CallNext --> Redis2{Redis Operations}

    Redis2 -->|ZRANGE| GetFirst[Get first in queue]
    Redis2 -->|HSET| UpdateStatus[Update status: WITH_DOCTOR]
    Redis2 -->|SET| SetCurrent[queue:current:2026-02-17<br/>Set current token]

    GetFirst --> Notify[Notify Patient]
    UpdateStatus --> Notify
    SetCurrent --> Notify

    Notify --> Complete[Consultation Complete]

    Complete --> Redis3{Redis Operations}
    Redis3 -->|HSET| FinalStatus[Update status: COMPLETED]
    Redis3 -->|ZREM| RemoveFromQueue[Remove from queue]

    FinalStatus --> NextPatient[Next Patient]
    RemoveFromQueue --> NextPatient

    style Redis1 fill:#e91e63
    style Redis2 fill:#e91e63
    style Redis3 fill:#e91e63
    style Token fill:#4caf50,color:#fff
    style NextPatient fill:#2196f3,color:#fff
```

### 🗄️ Database Schema Overview

```mermaid
erDiagram
    USERS ||--o{ APPOINTMENTS : creates
    USERS ||--o{ VISITS : conducts
    USERS {
        int id PK
        string username
        string email
        string password_hash
        enum role
        timestamp created_at
    }

    PATIENTS ||--o{ APPOINTMENTS : books
    PATIENTS ||--o{ VISITS : has
    PATIENTS {
        int id PK
        string name
        string phone
        date date_of_birth
        string address
        json allergies
        json chronic_conditions
        timestamp created_at
    }

    APPOINTMENTS ||--|| SLOTS : uses
    APPOINTMENTS ||--o| VISITS : converts_to
    APPOINTMENTS {
        int id PK
        int patient_id FK
        int slot_id FK
        enum status
        string notes
        timestamp created_at
    }

    SLOTS ||--|| USERS : assigned_to
    SLOTS {
        int id PK
        int doctor_id FK
        date date
        time start_time
        time end_time
        boolean is_blocked
        string block_reason
    }

    VISITS ||--o{ PRESCRIPTIONS : generates
    VISITS ||--o{ CLINICAL_NOTES : contains
    VISITS {
        int id PK
        int patient_id FK
        int doctor_id FK
        int appointment_id FK
        json vitals
        string chief_complaint
        string diagnosis
        string treatment_plan
        enum status
        timestamp created_at
    }

    PRESCRIPTIONS ||--o{ PRESCRIPTION_ITEMS : contains
    PRESCRIPTIONS ||--o| INVOICES : billed_in
    PRESCRIPTIONS {
        int id PK
        int visit_id FK
        int patient_id FK
        int doctor_id FK
        timestamp created_at
    }

    PRESCRIPTION_ITEMS }|--|| MEDICINES : prescribes
    PRESCRIPTION_ITEMS {
        int id PK
        int prescription_id FK
        int medicine_id FK
        string dosage
        string frequency
        int duration_days
        string instructions
    }

    MEDICINES ||--o{ MEDICINE_BATCHES : has
    MEDICINES {
        int id PK
        string name
        string generic_name
        string manufacturer
        decimal unit_price
        int reorder_level
    }

    MEDICINE_BATCHES ||--o{ DISPENSING_ITEMS : dispensed_from
    MEDICINE_BATCHES {
        int id PK
        int medicine_id FK
        string batch_number
        int quantity
        date expiry_date
        decimal cost_price
        timestamp created_at
    }

    INVOICES ||--o{ INVOICE_ITEMS : contains
    INVOICES ||--o| DISPENSING : triggers
    INVOICES {
        int id PK
        int patient_id FK
        int prescription_id FK
        enum mode
        decimal subtotal
        decimal discount
        decimal tax
        decimal total
        enum status
        enum payment_method
        timestamp paid_at
    }

    DISPENSING ||--o{ DISPENSING_ITEMS : contains
    DISPENSING {
        int id PK
        int prescription_id FK
        int invoice_id FK
        int pharmacist_id FK
        timestamp dispensed_at
    }

    DISPENSING_ITEMS {
        int id PK
        int dispensing_id FK
        int medicine_id FK
        int batch_id FK
        int quantity
        decimal unit_price
    }
```

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
