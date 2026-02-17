from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime, date, time
from decimal import Decimal
from app.models import (
    UserRole,
    AppointmentStatus,
    SlotType,
    VisitStatus,
    ClinicalNoteType,
    InvoiceStatus
)

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    role: UserRole


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    id: int
    is_active: int
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class PatientBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    age: int = Field(..., ge=0, le=150)
    phone: str = Field(..., min_length=10, max_length=15)
    email: Optional[str] = None
    blood_group: Optional[str] = Field(None, pattern="^(A|B|AB|O)[+-]$")
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=150)
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    email: Optional[str] = None
    blood_group: Optional[str] = Field(None, pattern="^(A|B|AB|O)[+-]$")
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None


class PatientResponse(PatientBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SlotBase(BaseModel):
    slot_date: date
    slot_time: time
    duration_minutes: int = Field(30, ge=15, le=120)
    slot_type: SlotType = SlotType.REGULAR


class SlotCreate(SlotBase):
    pass


class SlotUpdate(BaseModel):
    is_available: Optional[bool] = None
    is_blocked: Optional[bool] = None
    blocked_reason: Optional[str] = None


class SlotResponse(SlotBase):
    id: int
    is_available: bool
    is_blocked: bool
    blocked_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SlotBlockBase(BaseModel):
    doctor_id: int
    block_date: date
    start_time: time
    end_time: time
    reason: str = Field(..., min_length=1, max_length=200)


class SlotBlockCreate(SlotBlockBase):
    pass


class SlotBlockUpdate(BaseModel):
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    reason: Optional[str] = Field(None, min_length=1, max_length=200)


class SlotBlockResponse(SlotBlockBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AppointmentBase(BaseModel):
    patient_id: int
    appointment_date: datetime
    chief_complaint: Optional[str] = None


class AppointmentCreate(BaseModel):
    """
    Create appointment - appointment_date is auto-populated from slot_id
    """
    patient_id: int
    doctor_id: Optional[int] = None
    slot_id: int
    chief_complaint: Optional[str] = None


class AppointmentUpdate(BaseModel):
    doctor_id: Optional[int] = None
    appointment_date: Optional[datetime] = None
    status: Optional[AppointmentStatus] = None
    chief_complaint: Optional[str] = None
    notes: Optional[str] = None


class AppointmentResponse(AppointmentBase):
    id: int
    doctor_id: Optional[int] = None
    slot_id: Optional[int] = None
    status: AppointmentStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    patient: Optional[PatientResponse] = None
    slot: Optional[SlotResponse] = None

    class Config:
        from_attributes = True


class VisitBase(BaseModel):
    appointment_id: int
    patient_id: int
    chief_complaint: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    follow_up_date: Optional[datetime] = None


class VisitCreate(BaseModel):
    """
    Create visit - patient_id and doctor_id are auto-fetched from appointment
    """
    appointment_id: int
    blood_pressure: Optional[str] = Field(None, description="Blood pressure in mmHg (e.g., '120/80')")
    temperature: Optional[float] = Field(None, ge=90.0, le=110.0, description="Body temperature in Celsius (°C). Normal: 36.5-37.5°C, Fever: >38°C")
    pulse_rate: Optional[int] = Field(None, ge=40, le=200, description="Heart rate in beats per minute (bpm)")
    weight: Optional[float] = Field(None, ge=0, le=500, description="Body weight in kilograms (kg)")
    height: Optional[float] = Field(None, ge=0, le=300, description="Height in centimeters (cm)")
    chief_complaint: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None


class VisitUpdate(BaseModel):
    blood_pressure: Optional[str] = Field(None, description="Blood pressure in mmHg (e.g., '120/80')")
    temperature: Optional[float] = Field(None, ge=35.0, le=42.0, description="Body temperature in Celsius (°C). Normal: 36.5-37.5°C, Fever: >38°C")
    pulse_rate: Optional[int] = Field(None, ge=40, le=200, description="Heart rate in beats per minute (bpm)")
    weight: Optional[float] = Field(None, ge=0, le=500, description="Body weight in kilograms (kg)")
    height: Optional[float] = Field(None, ge=0, le=300, description="Height in centimeters (cm)")
    chief_complaint: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    status: Optional[VisitStatus] = None


class VisitResponse(VisitBase):
    id: int
    doctor_id: int
    blood_pressure: Optional[str] = None
    temperature: Optional[float] = None
    pulse_rate: Optional[int] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    status: VisitStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ClinicalNoteBase(BaseModel):
    visit_id: int
    note_type: ClinicalNoteType
    note_text: str = Field(..., min_length=1)


class ClinicalNoteCreate(BaseModel):
    """Create clinical note - visit_id comes from URL path"""
    note_type: ClinicalNoteType
    note_text: str = Field(..., min_length=1)


class ClinicalNoteUpdate(BaseModel):
    note_type: Optional[ClinicalNoteType] = None
    note_text: Optional[str] = Field(None, min_length=1)


class ClinicalNoteResponse(ClinicalNoteBase):
    id: int
    author_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class MedicineBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    generic_name: Optional[str] = Field(None, max_length=200)
    manufacturer: Optional[str] = Field(None, max_length=200)
    dosage_form: Optional[str] = Field(None, max_length=50)
    strength: Optional[str] = Field(None, max_length=50)
    unit_price: float = Field(..., ge=0)
    reorder_level: int = Field(10, ge=0)


class MedicineCreate(MedicineBase):
    pass


class MedicineUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    generic_name: Optional[str] = Field(None, max_length=200)
    manufacturer: Optional[str] = Field(None, max_length=200)
    dosage_form: Optional[str] = Field(None, max_length=50)
    strength: Optional[str] = Field(None, max_length=50)
    unit_price: Optional[float] = Field(None, ge=0)
    reorder_level: Optional[int] = Field(None, ge=0)


class MedicineResponse(MedicineBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BatchBase(BaseModel):
    medicine_id: int
    batch_number: str = Field(..., min_length=1, max_length=100)
    quantity: int = Field(..., ge=0)
    purchase_price: float = Field(..., ge=0)
    sale_price: float = Field(..., ge=0)
    manufacturing_date: Optional[date] = None
    expiry_date: date
    supplier: Optional[str] = Field(None, max_length=200)


class BatchCreate(BatchBase):
    pass


class BatchUpdate(BaseModel):
    quantity: Optional[int] = Field(None, ge=0)
    purchase_price: Optional[float] = Field(None, ge=0)
    sale_price: Optional[float] = Field(None, ge=0)
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    supplier: Optional[str] = Field(None, max_length=200)


class BatchResponse(BatchBase):
    id: int
    received_date: date
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PrescriptionItemBase(BaseModel):
    medicine_id: int
    dosage: str = Field(..., min_length=1, max_length=50)
    frequency: str = Field(..., min_length=1, max_length=50)
    duration_days: int = Field(..., ge=1, le=365)
    quantity: int = Field(..., ge=1)
    instructions: Optional[str] = None


class PrescriptionItemCreate(PrescriptionItemBase):
    pass


class PrescriptionItemResponse(PrescriptionItemBase):
    id: int
    prescription_id: int
    medicine: Optional[MedicineResponse] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PrescriptionBase(BaseModel):
    visit_id: int


class PrescriptionCreate(PrescriptionBase):
    items: List[PrescriptionItemCreate] = Field(..., min_length=1)


class PrescriptionUpdate(BaseModel):
    items: Optional[List[PrescriptionItemCreate]] = None


class PrescriptionResponse(PrescriptionBase):
    id: int
    prescribed_by: int
    is_dispensed: int
    dispensed_at: Optional[datetime] = None
    dispensed_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[PrescriptionItemResponse] = []
    patient: Optional[PatientResponse] = None

    class Config:
        from_attributes = True


class InvoiceItemBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=200)
    item_type: str = Field(..., min_length=1, max_length=50)
    quantity: int = Field(1, ge=1)
    unit_price: Decimal = Field(..., ge=0, decimal_places=2)
    total_price: Decimal = Field(..., ge=0, decimal_places=2)


class InvoiceItemCreate(InvoiceItemBase):
    medicine_id: Optional[int] = None


class InvoiceItemResponse(InvoiceItemBase):
    id: int
    invoice_id: int
    medicine_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InvoiceBase(BaseModel):
    patient_id: int


class InvoiceCreate(BaseModel):
    """
    Create invoice - TWO WAYS:

    1. AUTO MODE (Recommended): Just provide prescription_id
       - Auto-generates items from prescription (medicines + consultation fee)
       - Fetches prices from medicine catalog

    2. MANUAL MODE: Provide custom items
       - For walk-ins or custom billing
       - Must provide visit_id or patient_id
    """
    prescription_id: Optional[int] = Field(None, description="Prescription ID - auto-generates complete bill")
    visit_id: Optional[int] = Field(None, description="Visit ID - for manual billing without prescription")
    patient_id: Optional[int] = Field(None, description="Patient ID - for walk-ins")
    items: Optional[List[InvoiceItemCreate]] = Field(None, description="Custom items - only for manual billing")
    consultation_fee: float = Field(50.0, description="Consultation fee to add (default: 50.0)")
    payment_method: Optional[str] = None


class InvoiceUpdate(BaseModel):
    status: Optional[InvoiceStatus] = None
    subtotal: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    tax_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    discount_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    total_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    paid_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    payment_method: Optional[str] = None


class InvoiceResponse(InvoiceBase):
    id: int
    visit_id: Optional[int] = None
    prescription_id: Optional[int] = None
    invoice_date: datetime
    status: InvoiceStatus
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    payment_method: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[InvoiceItemResponse] = []
    patient: Optional[PatientResponse] = None

    class Config:
        from_attributes = True


class QueueTokenResponse(BaseModel):
    """Single queue token/entry"""
    token_number: int
    patient_id: int
    patient_name: str
    appointment_id: Optional[int] = None
    status: str
    checkin_time: datetime
    called_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    is_walk_in: bool = False


class QueueCheckInRequest(BaseModel):
    """Check-in an appointment"""
    appointment_id: int


class QueueWalkInRequest(BaseModel):
    """Add walk-in patient to queue"""
    patient_id: int
    chief_complaint: Optional[str] = None


class QueueStatusUpdate(BaseModel):
    """Update queue token status"""
    status: str = Field(..., pattern="^(WAITING|WITH_DOCTOR|COMPLETED|SKIPPED|NO_SHOW)$")


class QueueSummaryResponse(BaseModel):
    """Today's queue summary"""
    date: date
    total_tokens: int
    checked_in: int
    waiting: int
    with_doctor: int
    completed: int
    skipped: int
    no_show: int
    current_token: Optional[int] = None
    tokens: List[QueueTokenResponse] = []