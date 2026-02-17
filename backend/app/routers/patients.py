from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.database import get_db
from app.mongo_client import get_mongo_db
from app.services.mongo_services import AuditLogService
from app.models import Patient, User, Visit, Prescription
from app.schemas import PatientCreate, PatientUpdate, PatientResponse, VisitResponse, PrescriptionResponse
from app.auth import get_current_active_user

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient: PatientCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    mongo_db = Depends(get_mongo_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new patient with audit logging"""
    db_patient = Patient(**patient.model_dump())
    db.add(db_patient)
    await db.commit()
    await db.refresh(db_patient)

    try:
        audit_service = AuditLogService(mongo_db)
        await audit_service.log_action(
            user_id=current_user.id,
            username=current_user.username,
            action="CREATE",
            resource_type="patient",
            resource_id=db_patient.id,
            details={
                "patient_name": db_patient.name,
                "age": db_patient.age,
                "phone": db_patient.phone,
                "blood_group": db_patient.blood_group
            },
            ip_address=request.client.host if request.client else None
        )
    except Exception as e:
        print(f"MongoDB audit log failed: {e}")

    return db_patient


@router.get("", response_model=List[PatientResponse])
async def get_patients(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = Query(None, description="Search by name, phone, or patient ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List/search patients with pagination"""
    query = select(Patient)

    if search:
        query = query.where(
            or_(
                Patient.name.ilike(f"%{search}%"),
                Patient.phone.ilike(f"%{search}%"),
                Patient.id == int(search) if search.isdigit() else False
            )
        )

    query = query.offset(skip).limit(limit).order_by(Patient.id)
    result = await db.execute(query)
    patients = result.scalars().all()
    return patients


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific patient by ID"""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalars().first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found"
        )
    return patient


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    patient_update: PatientUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    mongo_db = Depends(get_mongo_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalars().first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found"
        )

    update_data = patient_update.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in update_data.items():
        if hasattr(patient, field) and value is not None:
            setattr(patient, field, value)

    await db.commit()
    await db.refresh(patient)

    try:
        audit_service = AuditLogService(mongo_db)
        await audit_service.log_action(
            user_id=current_user.id,
            username=current_user.username,
            action="UPDATE",
            resource_type="patient",
            resource_id=patient_id,
            details={
                "changes": update_data,
                "patient_name": patient.name
            },
            ip_address=request.client.host if request.client else None
        )
    except Exception as e:
        print(f"MongoDB audit log failed: {e}")

    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    mongo_db = Depends(get_mongo_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a patient with audit logging"""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalars().first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found"
        )

    patient_name = patient.name
    patient_phone = patient.phone

    await db.delete(patient)
    await db.commit()

    try:
        audit_service = AuditLogService(mongo_db)
        await audit_service.log_action(
            user_id=current_user.id,
            username=current_user.username,
            action="DELETE",
            resource_type="patient",
            resource_id=patient_id,
            details={
                "patient_name": patient_name,
                "patient_phone": patient_phone
            },
            ip_address=request.client.host if request.client else None
        )
    except Exception as e:
        print(f"MongoDB audit log failed: {e}")

    return None


@router.get("/{patient_id}/history", response_model=List[VisitResponse])
async def get_patient_history(
    patient_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get complete visit history for a patient"""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalars().first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found"
        )

    result = await db.execute(
        select(Visit)
        .where(Visit.patient_id == patient_id)
        .order_by(Visit.started_at.desc())
        .offset(skip)
        .limit(limit)
    )
    visits = result.scalars().all()
    return visits


@router.get("/{patient_id}/prescriptions", response_model=List[PrescriptionResponse])
async def get_patient_prescriptions(
    patient_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all prescriptions for a patient"""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalars().first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found"
        )

    result = await db.execute(
        select(Prescription)
        .options(selectinload(Prescription.items))
        .where(Prescription.patient_id == patient_id)
        .order_by(Prescription.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    prescriptions = result.scalars().all()
    return prescriptions
