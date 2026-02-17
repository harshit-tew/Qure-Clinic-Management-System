"""
Demo Database Seeder - Creates realistic clinic data with human imperfections
Run: python seed_demo_data.py
"""
import asyncio
from datetime import datetime, date, time, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.mongo_client import get_mongo_db
from app.services.mongo_services import VisitHistoryService, AuditLogService, StockMovementService
from app.models import (
    User, Patient, Appointment, Visit,
    Medicine, Batch, Prescription, PrescriptionItem, Invoice, InvoiceItem
)
from app.auth import get_password_hash
import random


# Realistic data with typos and casual entries
PATIENT_DATA = [
    {"name": "Rajesh Kumar", "age": 45, "phone": "9876543210", "address": "123 MG road, bangalore"},
    {"name": "Priya Sharma", "age": 32, "phone": "9876543211", "address": "45 koramangla, Banglore"},  # typo in Koramangala
    {"name": "Amit Patel", "age": 28, "phone": "9876543212", "address": "67 indra nagar"},  # missing city
    {"name": "Sneha Reddy", "age": 41, "phone": "9876543213", "address": "89 Jayanagar 4th block"},
    {"name": "Vikram Singh", "age": 55, "phone": "9876543214", "address": "12 whitfield, bangalor"},  # typo
    {"name": "Anjali Verma", "age": 29, "phone": "9876543215", "address": "34 HSR layout sector 2"},
    {"name": "Suresh Iyer", "age": 62, "phone": "9876543216", "address": "56 malleshwaram"},
    {"name": "Kavita Desai", "age": 37, "phone": "9876543217", "address": "78 RajajiNagar"},  # no space
    {"name": "Ramesh Gupta", "age": 48, "phone": "9876543218", "address": "90 BTM layout stage 2"},
    {"name": "Deepa Nair", "age": 34, "phone": "9876543219", "address": "23 electronic city phase1"},  # no space
    {"name": "Arun Kumar", "age": 52, "phone": "9876543220", "address": "45 yelahanka"},
    {"name": "Meera Joshi", "age": 26, "phone": "9876543221", "address": "67 jp nagar 7th phase"},
    {"name": "Karthik Rao", "age": 39, "phone": "9876543222", "address": "89 Marathalli bridge"},
    {"name": "Lakshmi Pillai", "age": 44, "phone": "9876543223", "address": "12 Sarjapur road"},
    {"name": "Naveen Choudhary", "age": 31, "phone": "9876543224", "address": "34 Bellandur"},
]

MEDICINE_DATA = [
    {"name": "Paracetamol 500mg", "generic_name": "Paracetamol", "dosage_form": "Tablet", "strength": "500mg", "unit_price": 2.50, "reorder_level": 100},
    {"name": "Ibuprofen 400mg", "generic_name": "Ibruprofen", "dosage_form": "Tablet", "strength": "400mg", "unit_price": 5.00, "reorder_level": 50},  # typo
    {"name": "Amoxicilin 250mg", "generic_name": "Amoxicillin", "dosage_form": "Capsule", "strength": "250mg", "unit_price": 8.00, "reorder_level": 75},  # typo
    {"name": "Cetirizine 10mg", "generic_name": "Cetirizine", "dosage_form": "tablet", "strength": "10mg", "unit_price": 3.50, "reorder_level": 80},  # lowercase
    {"name": "Omeprazole 20mg", "generic_name": "omeprazole", "dosage_form": "Capsule", "strength": "20mg", "unit_price": 12.00, "reorder_level": 60},  # lowercase
    {"name": "Azithromycin 500mg", "generic_name": "Azithromycin", "dosage_form": "Tablet", "strength": "500mg", "unit_price": 15.00, "reorder_level": 40},
    {"name": "Metformin 500mg", "generic_name": "Metformin", "dosage_form": "tablet", "strength": "500mg", "unit_price": 4.00, "reorder_level": 100},
    {"name": "Amlodipine 5mg", "generic_name": "Amlodipine", "dosage_form": "Tablet", "strength": "5mg", "unit_price": 6.00, "reorder_level": 70},
    {"name": "Cough Syrup", "generic_name": "Dextromethorphan", "dosage_form": "Syrup", "strength": "100ml", "unit_price": 45.00, "reorder_level": 30},
    {"name": "Vitamin D3 ", "generic_name": "Cholecalciferol", "dosage_form": "Capsule", "strength": "60000IU", "unit_price": 25.00, "reorder_level": 50},  # extra space
]

DIAGNOSES = [
    "viral fever since 3 days",
    "complaining of headche and body pain",  # typo
    "seasonal cold and cough",
    "gastric problem, acidity",
    "high BP, routine checkup",
    "diabetic followup",
    "throat infection snce 2 days",  # typo
    "skin rash on hands",
    "back pain lower back",
    "knee pain, difficulty walking",
    "routine health checkup",
    "stomach upset",
    "chest congestion",
    "allergic reaction to something",
    "general weakness n fatigue",  # casual 'n'
]

TREATMENTS = [
    "advised rest, plenty of fluids. prescribed paracetamol",
    "Tab Ibuprofen 400mg TDS for 3days",
    "Steam inhalation advised, cough syrup prescribed",
    "antacid prescribed, avoid spicy food",
    "BP medication continued, follow up after 1 month",
    "diabetes medication adjusted, check sugar levels regularly",
    "antibiotic course started for 5days",
    "skin cream prescribed, avoid scratching",
    "pain killer given, advised physiotherapy",
    "painkiller n rest advised",  # casual 'n'
    "all reports normal, continue healthy lifestyle",
    "ORS advised, bland diet for 2 days",
    "antihistamine prescribed",
    "avoid allergens, cetirizine prescribed",
    "multivitamin prescribed, improve diet",
]


async def create_users_and_doctors(db: AsyncSession):
    """Create admin, receptionist, and doctors"""
    print("Creating users and doctors...")

    # Admin
    admin = User(
        username="admin",
        email="admin@clinic.com",
        full_name="Dr. Admin",
        role="admin",
        hashed_password=get_password_hash("admin123"),
        is_active=True
    )
    db.add(admin)

    # Receptionist
    receptionist = User(
        username="reception",
        email="reception@clinic.com",
        full_name="Sunita Receptionist",
        role="receptionist",
        hashed_password=get_password_hash("reception123"),
        is_active=True
    )
    db.add(receptionist)

    # Doctors (as Users with role="doctor")
    doctors_data = [
        {"username": "dr.sharma", "email": "sharma@clinic.com", "full_name": "Dr. Arvind Sharma"},
        {"username": "dr.mehta", "email": "mehta@clinic.com", "full_name": "Dr. Priya Mehta"},
        {"username": "dr.kumar", "email": "kumar@clinic.com", "full_name": "Dr Rajesh Kumar"},  # missing dot
    ]

    doctors = []
    for doc_data in doctors_data:
        user = User(
            username=doc_data["username"],
            email=doc_data["email"],
            full_name=doc_data["full_name"],
            role="doctor",
            hashed_password=get_password_hash("doctor123"),
            is_active=True
        )
        db.add(user)
        doctors.append(user)

    await db.commit()
    print(f"✓ Created {len(doctors_data)} doctors + admin + receptionist")
    return doctors


async def create_patients(db: AsyncSession):
    """Create patients with realistic data"""
    print("Creating patients...")
    patients = []

    for p_data in PATIENT_DATA:
        patient = Patient(**p_data)
        db.add(patient)
        patients.append(patient)

    await db.commit()
    print(f"✓ Created {len(patients)} patients")
    return patients


async def create_medicines_and_stock(db: AsyncSession, mongo_db):
    """Create medicines and add stock with MongoDB logging"""
    print("Creating medicines and stock...")
    medicines = []
    stock_service = StockMovementService(mongo_db)

    for med_data in MEDICINE_DATA:
        medicine = Medicine(**med_data)
        db.add(medicine)
        medicines.append(medicine)

    await db.flush()

    # Add stock batches with typos in batch numbers
    batch_numbers = ["BATCH001", "Batch002", "BTCH003", "batch004", "BATCH-005", "BTCH006", "Batch007", "BATCH008", "btch009", "BATCH010"]
    suppliers = ["ABC Pharma", "XYZ Medicines", "MediSupply Co", "PharmaPlus", "HealthMeds Ltd"]

    for i, medicine in enumerate(medicines):
        # Create 2-3 batches per medicine
        num_batches = random.randint(2, 3)
        for j in range(num_batches):
            expiry_date = date.today() + timedelta(days=random.randint(180, 720))
            quantity = random.randint(50, 200)
            purchase_price = float(medicine.unit_price) * 0.6

            batch = Batch(
                medicine_id=medicine.id,
                batch_number=f"{batch_numbers[i]}-{j+1}",
                quantity=quantity,
                purchase_price=purchase_price,
                sale_price=float(medicine.unit_price),
                expiry_date=expiry_date,
                supplier=random.choice(suppliers),
                received_date=date.today() - timedelta(days=random.randint(5, 30))
            )
            db.add(batch)
            await db.flush()

            # Log to MongoDB (convert date to datetime)
            try:
                await stock_service.log_stock_in(
                    medicine_id=medicine.id,
                    medicine_name=medicine.name,
                    batch_id=batch.id,
                    batch_number=batch.batch_number,
                    quantity=quantity,
                    purchase_price=purchase_price,
                    sale_price=float(medicine.unit_price),
                    expiry_date=datetime.combine(expiry_date, time.min) if isinstance(expiry_date, date) else expiry_date,
                    supplier=batch.supplier,
                    performed_by_id=1,  # admin
                    performed_by_name="Dr. Admin"
                )
            except Exception as e:
                print(f"  MongoDB log failed: {e}")

    await db.commit()
    print(f"✓ Created {len(medicines)} medicines with stock batches")
    return medicines


async def create_appointments_and_visits(db: AsyncSession, mongo_db, patients, doctors):
    """Create past appointments, visits, prescriptions with realistic flow"""
    print("Creating appointments and visits...")
    visit_service = VisitHistoryService(mongo_db)
    audit_service = AuditLogService(mongo_db)
    stock_service = StockMovementService(mongo_db)

    # Create appointments over past 14 days
    visits_created = 0
    prescriptions_created = 0

    for day_offset in range(14, 0, -1):
        appt_date = date.today() - timedelta(days=day_offset)

        # 3-5 appointments per day
        num_appointments = random.randint(3, 5)
        selected_patients = random.sample(patients, num_appointments)

        for i, patient in enumerate(selected_patients):
            doctor = random.choice(doctors)
            appt_time = time(hour=random.randint(9, 16), minute=random.choice([0, 30]))
            appt_datetime = datetime.combine(appt_date, appt_time)

            # Create appointment
            appointment = Appointment(
                patient_id=patient.id,
                doctor_id=doctor.id,
                appointment_date=appt_datetime,
                chief_complaint=random.choice(DIAGNOSES),
                status=random.choice(["COMPLETED", "COMPLETED", "COMPLETED", "CANCELLED"])  # mostly completed
            )
            db.add(appointment)
            await db.flush()

            # If completed, create visit
            if appointment.status == "COMPLETED":
                is_completed = random.choice([True, True, False])  # mostly completed
                visit = Visit(
                    appointment_id=appointment.id,
                    patient_id=patient.id,
                    doctor_id=doctor.id,
                    chief_complaint=appointment.chief_complaint,
                    diagnosis=random.choice(DIAGNOSES),
                    treatment_plan=random.choice(TREATMENTS),
                    status="COMPLETED" if is_completed else "IN_PROGRESS"
                )

                # Add vitals with realistic ranges
                visit.blood_pressure = f"{random.randint(110, 140)}/{random.randint(70, 90)}"
                visit.temperature = round(random.uniform(97.5, 99.5), 1)
                visit.pulse_rate = random.randint(65, 85)
                visit.weight = round(random.uniform(50, 85), 1)
                visit.height = round(random.uniform(150, 180), 0)

                db.add(visit)
                await db.flush()
                visits_created += 1

                # Create prescription (80% chance)
                if random.random() < 0.8:
                    # Get medicines
                    result = await db.execute(select(Medicine))
                    all_medicines = result.scalars().all()

                    prescription = Prescription(
                        visit_id=visit.id,
                        patient_id=patient.id,
                        prescribed_by=doctor.id,
                        is_dispensed=random.choice([0, 0, 1])  # mostly not dispensed yet
                    )
                    db.add(prescription)
                    await db.flush()

                    # Add 1-3 medicines
                    num_meds = random.randint(1, 3)
                    selected_meds = random.sample(all_medicines, min(num_meds, len(all_medicines)))

                    for med in selected_meds:
                        duration_days = random.choice([3, 5, 7, 10])
                        item = PrescriptionItem(
                            prescription_id=prescription.id,
                            medicine_id=med.id,
                            dosage="500mg",
                            frequency=random.choice(["1-0-1", "1-1-1", "0-0-1", "1-0-0"]),
                            duration_days=duration_days,
                            quantity=random.randint(5, 20),
                            instructions="Take after meals"
                        )
                        db.add(item)

                    await db.flush()
                    prescriptions_created += 1

                    # If dispensed, deduct stock
                    if prescription.is_dispensed:
                        result = await db.execute(
                            select(PrescriptionItem).where(PrescriptionItem.prescription_id == prescription.id)
                        )
                        items = result.scalars().all()

                        for item in items:
                            # Get oldest batch with stock
                            result = await db.execute(
                                select(Batch)
                                .where(Batch.medicine_id == item.medicine_id, Batch.quantity > 0)
                                .order_by(Batch.expiry_date)
                            )
                            batch = result.scalars().first()

                            if batch and batch.quantity >= item.quantity:
                                batch.quantity -= item.quantity

                                # Log to MongoDB
                                try:
                                    result = await db.execute(select(Medicine).where(Medicine.id == item.medicine_id))
                                    medicine = result.scalars().first()

                                    await stock_service.log_stock_out(
                                        medicine_id=medicine.id,
                                        medicine_name=medicine.name,
                                        batch_id=batch.id,
                                        batch_number=batch.batch_number,
                                        quantity=item.quantity,
                                        reason="DISPENSED",
                                        reference_type="prescription",
                                        reference_id=prescription.id,
                                        performed_by_id=2,  # receptionist
                                        performed_by_name="Sunita Receptionist"
                                    )
                                except Exception as e:
                                    print(f"  MongoDB stock log failed: {e}")

                # If visit completed, create MongoDB document
                if visit.status == "COMPLETED":
                    try:
                        # Get prescription details
                        prescriptions_data = []
                        if prescription:
                            result = await db.execute(
                                select(PrescriptionItem)
                                .where(PrescriptionItem.prescription_id == prescription.id)
                            )
                            items = result.scalars().all()

                            for item in items:
                                result = await db.execute(select(Medicine).where(Medicine.id == item.medicine_id))
                                med = result.scalars().first()
                                prescriptions_data.append({
                                    "medicine_name": med.name if med else "Unknown",
                                    "quantity": item.quantity,
                                    "dosage": f"{item.dosage} {item.frequency}",
                                    "duration": f"{item.duration_days} days"
                                })

                        await visit_service.create_visit_document(
                            visit_id=visit.id,
                            patient_id=patient.id,
                            patient_name=patient.name,
                            patient_age=patient.age,
                            patient_gender="",  # Not available in model
                            doctor_id=doctor.id,
                            doctor_name=doctor.full_name,
                            visit_date=appt_date,
                            chief_complaint=visit.chief_complaint,
                            diagnosis=visit.diagnosis,
                            treatment_plan=visit.treatment_plan,
                            vitals={
                                "blood_pressure": visit.blood_pressure,
                                "temperature": float(visit.temperature) if visit.temperature else None,
                                "pulse_rate": visit.pulse_rate,
                                "weight": float(visit.weight) if visit.weight else None,
                                "height": float(visit.height) if visit.height else None
                            },
                            prescriptions=prescriptions_data
                        )
                    except Exception as e:
                        print(f"  MongoDB visit log failed: {e}")

                # Create billing invoice
                consultation_fee = 500.0  # Fixed consultation fee
                is_paid = random.random() < 0.9  # 90% paid
                invoice = Invoice(
                    patient_id=patient.id,
                    visit_id=visit.id,
                    subtotal=consultation_fee,
                    total_amount=consultation_fee,
                    paid_amount=consultation_fee if is_paid else 0.0,
                    status="PAID" if is_paid else "PENDING",
                    payment_method=random.choice(["cash", "card", "upi", "upi", "cash"])
                )
                db.add(invoice)
                await db.flush()

                # Add consultation fee item
                invoice_item = InvoiceItem(
                    invoice_id=invoice.id,
                    item_type="consultation",
                    description="Consultation Fee",
                    quantity=1,
                    unit_price=consultation_fee,
                    total_price=consultation_fee
                )
                db.add(invoice_item)

    await db.commit()
    print(f"✓ Created appointments with {visits_created} visits and {prescriptions_created} prescriptions")


async def create_today_appointments(db: AsyncSession, patients, doctors):
    """Create today's appointments for demo"""
    print("Creating today's appointments...")

    # Select 5 random patients for today
    today_patients = random.sample(patients, 5)
    time_slots = [
        time(9, 0), time(10, 0), time(11, 0), time(14, 0), time(15, 0)
    ]

    for i, patient in enumerate(today_patients):
        doctor = random.choice(doctors)
        appt_datetime = datetime.combine(date.today(), time_slots[i])
        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_date=appt_datetime,
            chief_complaint=random.choice(DIAGNOSES),
            status=random.choice(["SCHEDULED", "SCHEDULED", "CHECKED_IN"])
        )
        db.add(appointment)

    await db.commit()
    print(f"✓ Created 5 appointments for today")


async def log_audit_entries(db: AsyncSession, mongo_db):
    """Create audit log entries for some actions"""
    print("Creating audit log entries...")
    audit_service = AuditLogService(mongo_db)

    # Get some patients
    result = await db.execute(select(Patient).limit(5))
    patients = result.scalars().all()

    try:
        for patient in patients:
            # Create patient audit log
            await audit_service.log_action(
                user_id=2,
                username="reception",
                action="CREATE",
                resource_type="patient",
                resource_id=patient.id,
                details={
                    "patient_name": patient.name,
                    "phone": patient.phone,
                    "created_via": "registration_form"
                },
                ip_address="192.168.1.100"
            )

            # Update audit log (random)
            if random.random() < 0.3:
                await audit_service.log_action(
                    user_id=2,
                    username="reception",
                    action="UPDATE",
                    resource_type="patient",
                    resource_id=patient.id,
                    details={
                        "patient_name": patient.name,
                        "fields_updated": ["phone", "address"],
                        "reason": "patient requested update"
                    },
                    ip_address="192.168.1.100"
                )

        print(f"✓ Created audit log entries")
    except Exception as e:
        print(f"  MongoDB audit log failed: {e}")


async def main():
    """Run the seeder"""
    print("=" * 60)
    print("🌱 Starting Demo Database Seeder")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        mongo_db = await get_mongo_db()

        # Clear existing data warning
        print("\n⚠️  This will populate your database with demo data!")
        print("Make sure your containers are running:")
        print("  docker-compose up -d")
        print("\nStarting in 3 seconds...")
        await asyncio.sleep(3)

        # Seed in order
        doctors = await create_users_and_doctors(db)
        patients = await create_patients(db)
        medicines = await create_medicines_and_stock(db, mongo_db)
        await create_appointments_and_visits(db, mongo_db, patients, doctors)
        await create_today_appointments(db, patients, doctors)
        await log_audit_entries(db, mongo_db)

        print("\n" + "=" * 60)
        print("✅ Database seeding completed!")
        print("=" * 60)
        print("\n📊 Summary:")
        print(f"  • {len(doctors)} doctors")
        print(f"  • {len(patients)} patients")
        print(f"  • {len(medicines)} medicines with stock")
        print(f"  • Past 14 days of appointments and visits")
        print(f"  • 5 appointments for today")
        print(f"  • MongoDB logs (visit history, audit, stock movements)")
        print("\n🎯 Login Credentials:")
        print("  Admin: admin / admin123")
        print("  Receptionist: reception / reception123")
        print("  Doctors: dr.sharma, dr.mehta, dr.kumar / doctor123")
        print("\n🚀 Start server: uvicorn app.main:app --reload")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
