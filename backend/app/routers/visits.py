from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime
from app.database import get_db
from app.mongo_client import get_mongo_db
from app.services.mongo_services import VisitHistoryService
from app.models import User, Visit, Appointment, AppointmentStatus, VisitStatus, ClinicalNote, Patient, Prescription, PrescriptionItem
from app.schemas import (
    VisitCreate,
    VisitUpdate,
    VisitResponse,
    ClinicalNoteCreate,
    ClinicalNoteResponse
)
from app.auth import get_current_active_user

router = APIRouter(prefix="/visits", tags=["Visits"])


@router.post("", response_model=VisitResponse, status_code=status.HTTP_201_CREATED)
async def start_visit(
    visit: VisitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.patient))
        .where(Appointment.id == visit.appointment_id)
    )
    appointment = result.scalars().first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {visit.appointment_id} not found"
        )

    if not appointment.patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment has no patient associated"
        )

    if not appointment.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment has no doctor assigned"
        )

    result = await db.execute(
        select(Visit).where(Visit.appointment_id == visit.appointment_id)
    )
    existing_visit = result.scalars().first()

    if existing_visit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Visit already exists for this appointment"
        )

    appointment.status = AppointmentStatus.WITH_DOCTOR

    db_visit = Visit(
        appointment_id=visit.appointment_id,
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        blood_pressure=visit.blood_pressure,
        temperature=visit.temperature,
        pulse_rate=visit.pulse_rate,
        weight=visit.weight,
        height=visit.height,
        chief_complaint=visit.chief_complaint,
        diagnosis=visit.diagnosis,
        treatment_plan=visit.treatment_plan,
        status=VisitStatus.IN_PROGRESS
    )

    db.add(db_visit)
    await db.commit()
    await db.refresh(db_visit)
    return db_visit


@router.get("/{visit_id}", response_model=VisitResponse)
async def get_visit(
    visit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(
        select(Visit)
        .options(selectinload(Visit.clinical_notes))
        .where(Visit.id == visit_id)
    )
    visit = result.scalars().first()

    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Visit with ID {visit_id} not found"
        )

    return visit


@router.patch("/{visit_id}", response_model=VisitResponse)
async def update_visit(
    visit_id: int,
    visit_update: VisitUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = result.scalars().first()

    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Visit with ID {visit_id} not found"
        )

    if visit.status == VisitStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a completed visit"
        )

    update_data = visit_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(visit, field):
            setattr(visit, field, value)

    await db.commit()
    await db.refresh(visit)
    return visit


@router.patch("/{visit_id}/complete", response_model=VisitResponse)
async def complete_visit(
    visit_id: int,
    db: AsyncSession = Depends(get_db),
    mongo_db = Depends(get_mongo_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = result.scalars().first()

    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Visit with ID {visit_id} not found"
        )

    if visit.status == VisitStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Visit is already completed"
        )

    visit.status = VisitStatus.COMPLETED
    visit.completed_at = datetime.utcnow()

    result = await db.execute(
        select(Appointment).where(Appointment.id == visit.appointment_id)
    )
    appointment = result.scalars().first()
    if appointment:
        appointment.status = AppointmentStatus.COMPLETED

    await db.commit()
    await db.refresh(visit)

    try:
        patient_result = await db.execute(select(Patient).where(Patient.id == visit.patient_id))
        patient = patient_result.scalars().first()

        doctor_result = await db.execute(select(User).where(User.id == visit.doctor_id))
        doctor = doctor_result.scalars().first()

        prescriptions_result = await db.execute(
            select(Prescription)
            .options(selectinload(Prescription.items).selectinload(PrescriptionItem.medicine))
            .where(Prescription.visit_id == visit_id)
        )
        prescriptions = prescriptions_result.scalars().all()

        prescriptions_data = []
        for presc in prescriptions:
            presc_items = [
                {
                    "medicine_name": item.medicine.name,
                    "medicine_strength": item.medicine.strength,
                    "dosage": item.dosage,
                    "frequency": item.frequency,
                    "duration_days": item.duration_days,
                    "quantity": item.quantity,
                    "instructions": item.instructions
                }
                for item in presc.items
            ]
            prescriptions_data.append({
                "prescription_id": presc.id,
                "prescribed_at": presc.created_at.isoformat(),
                "items": presc_items
            })

        visit_service = VisitHistoryService(mongo_db)
        await visit_service.create_visit_document(
            visit_id=visit.id,
            patient_id=patient.id if patient else visit.patient_id,
            patient_name=patient.name if patient else "Unknown",
            doctor_id=doctor.id if doctor else visit.doctor_id,
            doctor_name=doctor.full_name if doctor else "Unknown",
            visit_date=visit.started_at,
            vitals={
                "blood_pressure": visit.blood_pressure,
                "temperature": float(visit.temperature) if visit.temperature else None,
                "pulse_rate": visit.pulse_rate,
                "weight": float(visit.weight) if visit.weight else None,
                "height": float(visit.height) if visit.height else None
            },
            chief_complaint=visit.chief_complaint or "",
            diagnosis=visit.diagnosis or "",
            treatment_plan=visit.treatment_plan or "",
            prescriptions=prescriptions_data
        )
    except Exception as e:
        print(f"MongoDB visit history creation failed: {e}")

    return visit


@router.post("/{visit_id}/notes", response_model=ClinicalNoteResponse, status_code=status.HTTP_201_CREATED)
async def add_clinical_note(
    visit_id: int,
    note: ClinicalNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = result.scalars().first()

    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Visit with ID {visit_id} not found"
        )

    db_note = ClinicalNote(
        visit_id=visit_id,
        note_type=note.note_type,
        note_text=note.note_text,
        author_id=current_user.id
    )
    db.add(db_note)
    await db.commit()
    await db.refresh(db_note)
    return db_note


@router.get("/{visit_id}/notes", response_model=List[ClinicalNoteResponse])
async def get_visit_notes(
    visit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all clinical notes for a visit"""
    result = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = result.scalars().first()

    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Visit with ID {visit_id} not found"
        )

    result = await db.execute(
        select(ClinicalNote)
        .where(ClinicalNote.visit_id == visit_id)
        .order_by(ClinicalNote.created_at)
    )
    notes = result.scalars().all()
    return notes


@router.get("/patient/{patient_id}/history-docs")
async def get_patient_visit_history_from_mongo(
    patient_id: int,
    skip: int = 0,
    limit: int = 10,
    mongo_db = Depends(get_mongo_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get patient visit history from MongoDB (FAST - no joins!)

    Returns denormalized documents with complete visit data including:
    - Patient and doctor info
    - Vitals
    - Diagnosis and treatment plan
    - All prescriptions with medicines
    """
    visit_service = VisitHistoryService(mongo_db)
    history = await visit_service.get_patient_history(
        patient_id=patient_id,
        skip=skip,
        limit=limit
    )
    return {
        "patient_id": patient_id,
        "total_visits": len(history),
        "visits": history
    }