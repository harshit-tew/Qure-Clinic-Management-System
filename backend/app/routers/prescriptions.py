from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from app.database import get_db
from app.models import User, Prescription, PrescriptionItem, Visit, Patient
from app.schemas import PrescriptionCreate, PrescriptionUpdate, PrescriptionResponse
from app.auth import get_current_active_user

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])


@router.post("", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_prescription(
    prescription: PrescriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Visit).where(Visit.id == prescription.visit_id))
    visit = result.scalars().first()

    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Visit with ID {prescription.visit_id} not found"
        )

    result = await db.execute(select(Patient).where(Patient.id == visit.patient_id))
    patient = result.scalars().first()


    db_prescription = Prescription(
        visit_id=prescription.visit_id,
        patient_id=visit.patient_id,
        prescribed_by=current_user.id,
        is_dispensed=0
    )
    db.add(db_prescription)
    await db.flush()

    for item in prescription.items:
        db_item = PrescriptionItem(
            prescription_id=db_prescription.id,
            **item.model_dump()
        )
        db.add(db_item)

    await db.commit()
    await db.refresh(db_prescription)

    result = await db.execute(
        select(Prescription)
        .options(
            selectinload(Prescription.items).selectinload(PrescriptionItem.medicine),
            selectinload(Prescription.patient)
        )
        .where(Prescription.id == db_prescription.id)
    )
    prescription_with_items = result.scalars().first()
    return prescription_with_items


@router.get("/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription(
    prescription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get prescription details"""
    result = await db.execute(
        select(Prescription)
        .options(
            selectinload(Prescription.items).selectinload(PrescriptionItem.medicine),
            selectinload(Prescription.patient)
        )
        .where(Prescription.id == prescription_id)
    )
    prescription = result.scalars().first()

    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription with ID {prescription_id} not found"
        )

    return prescription


@router.get("/{prescription_id}/print")
async def get_printable_prescription(
    prescription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get prescription in printable format"""
    result = await db.execute(
        select(Prescription)
        .options(
            selectinload(Prescription.items).selectinload(PrescriptionItem.medicine),
            selectinload(Prescription.patient),
            selectinload(Prescription.prescriber)
        )
        .where(Prescription.id == prescription_id)
    )
    prescription = result.scalars().first()

    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription with ID {prescription_id} not found"
        )

    printable_data = {
        "prescription_id": prescription.id,
        "date": prescription.created_at.strftime("%Y-%m-%d"),
        "patient": {
            "name": prescription.patient.name,
            "age": prescription.patient.age,
            "phone": prescription.patient.phone
        },
        "doctor": {
            "name": prescription.prescriber.full_name
        },
        "medicines": [
            {
                "name": item.medicine.name,
                "dosage": item.dosage,
                "frequency": item.frequency,
                "duration": f"{item.duration_days} days",
                "quantity": item.quantity,
                "instructions": item.instructions or ""
            }
            for item in prescription.items
        ]
    }

    return printable_data


@router.patch("/{prescription_id}", response_model=PrescriptionResponse)
async def update_prescription(
    prescription_id: int,
    prescription_update: PrescriptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(
        select(Prescription).where(Prescription.id == prescription_id)
    )
    prescription = result.scalars().first()

    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription with ID {prescription_id} not found"
        )

    if prescription.is_dispensed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify prescription that has already been dispensed"
        )

    if prescription_update.items:
        await db.execute(
            select(PrescriptionItem).where(PrescriptionItem.prescription_id == prescription_id)
        )
        for item in await db.execute(
            select(PrescriptionItem).where(PrescriptionItem.prescription_id == prescription_id)
        ):
            await db.delete(item.scalars().first())

        for item in prescription_update.items:
            db_item = PrescriptionItem(
                prescription_id=prescription_id,
                **item.model_dump()
            )
            db.add(db_item)

    await db.commit()
    await db.refresh(prescription)

    result = await db.execute(
        select(Prescription)
        .options(
            selectinload(Prescription.items).selectinload(PrescriptionItem.medicine),
            selectinload(Prescription.patient)
        )
        .where(Prescription.id == prescription_id)
    )
    prescription_with_items = result.scalars().first()
    return prescription_with_items