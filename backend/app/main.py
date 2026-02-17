from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from app.database import init_db
from app.redis_client import close_redis
from app.mongo_client import close_mongo, get_mongo_db

load_dotenv()
from app.routers import (
    auth,
    users,
    patients,
    appointments,
    slots,
    visits,
    prescriptions,
    inventory,
    dispensing,
    billing,
    reports,
    queue
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = await get_mongo_db()
    await create_mongo_indexes(db)
    print("MongoDB connected")

    yield

    await close_redis()
    await close_mongo()
    print(" Redis connection closed")
    print(" MongoDB connection closed")
    print(" Application shutdown")


async def create_mongo_indexes(db):
    await db.visit_history.create_index([("patient.id", 1), ("visit_date", -1)])
    await db.visit_history.create_index([("visit_id", 1)], unique=True)

    await db.audit_logs.create_index([("timestamp", -1)])
    await db.audit_logs.create_index([("user.id", 1), ("timestamp", -1)])
    await db.audit_logs.create_index([("resource.type", 1), ("timestamp", -1)])

    await db.stock_movements.create_index([("medicine.id", 1), ("timestamp", -1)])
    await db.stock_movements.create_index([("timestamp", -1)])
    await db.stock_movements.create_index([("movement_type", 1), ("timestamp", -1)])

    await db.daily_summaries.create_index([("date", -1)], unique=True)


app = FastAPI(
    title="Clinic Management System",
    description="Complete API for managing clinic operations with integrated pharmacy",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


app.include_router(auth.router)
app.include_router(users.router)

app.include_router(patients.router)

app.include_router(appointments.router)
app.include_router(slots.router)

app.include_router(queue.router)

app.include_router(visits.router)
app.include_router(prescriptions.router)

app.include_router(inventory.router)
app.include_router(dispensing.router)

app.include_router(billing.router)

app.include_router(reports.router)


@app.get("/")
def read_root():
    return {
        "message": "Welcome to Clinic Management System API",
        "version": "3.0.0",
        "description": "Complete clinic management system with integrated pharmacy",
        "modules": {
            "authentication": "JWT-based user authentication",
            "users": "User management (Admin, Doctor, Receptionist, Pharmacist)",
            "patients": "Patient registration and medical history",
            "appointments": "Appointment scheduling with slot management",
            "queue": "Real-time queue management with Redis",
            "visits": "Clinical consultations with vitals and notes",
            "prescriptions": "Digital prescription management",
            "inventory": "Medicine catalog and batch-based stock tracking",
            "dispensing": "FIFO-based medicine dispensing",
            "billing": "Invoice generation and payment tracking",
            "reports": "Analytics and reports"
        },
        "documentation": {
            "interactive": "/docs",
            "alternative": "/redoc"
        },
        "tech_stack": {
            "framework": "FastAPI",
            "database": "PostgreSQL (relational data)",
            "orm": "SQLAlchemy (async)",
            "cache": "Redis (queue management)",
            "document_store": "MongoDB (logs & analytics)",
            "auth": "JWT Bearer Token"
        }
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
