from sqlalchemy import Column, Integer, String, DateTime, Date, Time, ForeignKey, Enum, Text, Float, Boolean, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    RECEPTIONIST = "receptionist"
    PHARMACIST = "pharmacist"


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CHECKED_IN = "checked_in"
    WITH_DOCTOR = "with_doctor"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class VisitStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class SlotType(str, enum.Enum):
    REGULAR = "regular"
    EMERGENCY = "emergency"
    FOLLOW_UP = "follow_up"


class ClinicalNoteType(str, enum.Enum):
    SYMPTOM = "symptom"
    OBSERVATION = "observation"
    DIAGNOSIS = "diagnosis"
    TREATMENT_PLAN = "treatment_plan"
    GENERAL = "general"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"



class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    visits_as_doctor = relationship("Visit", foreign_keys="Visit.doctor_id", back_populates="doctor")
    prescriptions_created = relationship("Prescription", foreign_keys="Prescription.prescribed_by", back_populates="prescriber")
    prescriptions_dispensed = relationship("Prescription", foreign_keys="Prescription.dispensed_by", back_populates="dispenser")
    clinical_notes = relationship("ClinicalNote", back_populates="author")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    age = Column(Integer, nullable=False)
    phone = Column(String(15), nullable=False, index=True)
    email = Column(String(100), nullable=True)
    blood_group = Column(String(5), nullable=True)
    address = Column(Text, nullable=True)
    emergency_contact = Column(String(100), nullable=True)
    allergies = Column(Text, nullable=True)
    chronic_conditions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    appointments = relationship("Appointment", back_populates="patient")
    visits = relationship("Visit", back_populates="patient")
    prescriptions = relationship("Prescription", back_populates="patient")
    invoices = relationship("Invoice", back_populates="patient")


class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True)
    slot_date = Column(Date, nullable=False, index=True)
    slot_time = Column(Time, nullable=False, index=True)
    duration_minutes = Column(Integer, default=30, nullable=False)
    slot_type = Column(Enum(SlotType), default=SlotType.REGULAR)
    is_available = Column(Boolean, default=True, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)
    blocked_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    appointments = relationship("Appointment", back_populates="slot")


class SlotBlock(Base):
    """
    Used by doctors to mark 'Out of Office' or lunch breaks.
    Blocks multiple slots for a given date/time range.
    """
    __tablename__ = "slot_blocks"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    block_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    reason = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    doctor = relationship("User")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=True, index=True)
    appointment_date = Column(DateTime, nullable=False, index=True)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED)
    chief_complaint = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("User")
    slot = relationship("Slot", back_populates="appointments")
    visit = relationship("Visit", back_populates="appointment", uselist=False)


class Visit(Base):
    """
    The 'Header' for a doctor's visit.
    Contains diagnosis, vitals, and links to clinical notes.
    """
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False, unique=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    blood_pressure = Column(String(20), nullable=True)
    temperature = Column(Float, nullable=True)
    pulse_rate = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True)
    height = Column(Float, nullable=True)

    chief_complaint = Column(Text, nullable=True)
    diagnosis = Column(Text, nullable=True)
    treatment_plan = Column(Text, nullable=True)
    follow_up_date = Column(DateTime, nullable=True)

    status = Column(Enum(VisitStatus), default=VisitStatus.IN_PROGRESS)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    appointment = relationship("Appointment", back_populates="visit")
    patient = relationship("Patient", back_populates="visits")
    doctor = relationship("User", foreign_keys=[doctor_id], back_populates="visits_as_doctor")
    clinical_notes = relationship("ClinicalNote", back_populates="visit", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="visit")


class ClinicalNote(Base):
    """
    Granular notes added during the visit.
    Can be categorized by type (Symptom, Observation, etc.)
    """
    __tablename__ = "clinical_notes"

    id = Column(Integer, primary_key=True, index=True)
    visit_id = Column(Integer, ForeignKey("visits.id"), nullable=False, index=True)
    note_type = Column(Enum(ClinicalNoteType), nullable=False)
    note_text = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    visit = relationship("Visit", back_populates="clinical_notes")
    author = relationship("User", back_populates="clinical_notes")


class Medicine(Base):
    """
    The catalog entry for medicines.
    Name, generic name, unit type, etc.
    """
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    generic_name = Column(String(200), nullable=True, index=True)
    manufacturer = Column(String(200), nullable=True)
    dosage_form = Column(String(50), nullable=True)
    strength = Column(String(50), nullable=True)
    unit_price = Column(Float, nullable=False)
    reorder_level = Column(Integer, default=10)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batches = relationship("Batch", back_populates="medicine", cascade="all, delete-orphan")
    prescription_items = relationship("PrescriptionItem", back_populates="medicine")


class Batch(Base):
    """
    Physical stock tracker.
    Each purchase creates a new batch with batch number, expiry, quantity, and prices.
    """
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)
    batch_number = Column(String(100), nullable=False, unique=True, index=True)
    quantity = Column(Integer, nullable=False)
    purchase_price = Column(Float, nullable=False)
    sale_price = Column(Float, nullable=False)
    manufacturing_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=False, index=True)
    supplier = Column(String(200), nullable=True)
    received_date = Column(Date, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    medicine = relationship("Medicine", back_populates="batches")


class Prescription(Base):
    """
    The 'Order' linking a Visit to the Pharmacy.
    """
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    visit_id = Column(Integer, ForeignKey("visits.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    prescribed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_dispensed = Column(Integer, default=0)
    dispensed_at = Column(DateTime, nullable=True)
    dispensed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    visit = relationship("Visit", back_populates="prescriptions")
    patient = relationship("Patient", back_populates="prescriptions")
    prescriber = relationship("User", foreign_keys=[prescribed_by], back_populates="prescriptions_created")
    dispenser = relationship("User", foreign_keys=[dispensed_by], back_populates="prescriptions_dispensed")
    items = relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")


class PrescriptionItem(Base):
    """
    Individual line items in a prescription.
    Links to Medicine, specifies dosage, frequency, quantity.
    """
    __tablename__ = "prescription_items"

    id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=False, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)
    dosage = Column(String(50), nullable=False)
    frequency = Column(String(50), nullable=False)
    duration_days = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    instructions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    prescription = relationship("Prescription", back_populates="items")
    medicine = relationship("Medicine", back_populates="prescription_items")


class Invoice(Base):
    """
    The financial record for a visit or medication dispense.
    """
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    visit_id = Column(Integer, ForeignKey("visits.id"), nullable=True, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=True, index=True)
    invoice_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    subtotal = Column(Numeric(10, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(10, 2), nullable=False, default=0)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)
    paid_amount = Column(Numeric(10, 2), nullable=False, default=0)
    payment_method = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", back_populates="invoices")
    visit = relationship("Visit")
    prescription = relationship("Prescription")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    """
    Line items for consultation fees or specific medicines.
    """
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    description = Column(String(200), nullable=False)
    item_type = Column(String(50), nullable=False)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=True)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="items")
    medicine = relationship("Medicine")