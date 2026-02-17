from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import date, datetime
from app.database import get_db
from app.models import Appointment, Patient, User, Slot, AppointmentStatus
from app.schemas import AppointmentCreate, AppointmentUpdate, AppointmentResponse
from app.auth import get_current_active_user

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new appointment - appointment date/time is automatically derived from slot"""
    result = await db.execute(select(Patient).where(Patient.id == appointment.patient_id))
    patient = result.scalars().first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {appointment.patient_id} not found"
        )

    result = await db.execute(select(Slot).where(Slot.id == appointment.slot_id))
    slot = result.scalars().first()

    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slot with ID {appointment.slot_id} not found"
        )

    if not slot.is_available or slot.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slot is not available for booking"
        )

    appointment_datetime = datetime.combine(slot.slot_date, slot.slot_time)

    db_appointment = Appointment(
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        slot_id=appointment.slot_id,
        appointment_date=appointment_datetime,
        chief_complaint=appointment.chief_complaint,
        status=AppointmentStatus.SCHEDULED
    )

    slot.is_available = False

    db.add(db_appointment)
    await db.commit()
    await db.refresh(db_appointment)

    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.patient), selectinload(Appointment.slot))
        .where(Appointment.id == db_appointment.id)
    )
    db_appointment = result.scalars().first()

    return db_appointment


@router.get("", response_model=List[AppointmentResponse])
async def get_appointments(
    skip: int = 0,
    limit: int = 100,
    appointment_date: Optional[date] = Query(None, description="Filter by date"),
    status: Optional[AppointmentStatus] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all appointments with optional filters"""
    query = select(Appointment).options(
        selectinload(Appointment.patient),
        selectinload(Appointment.slot)
    )

    if appointment_date:
        query = query.where(Appointment.appointment_date >= datetime.combine(appointment_date, datetime.min.time()))

    if status:
        query = query.where(Appointment.status == status)

    query = query.order_by(Appointment.appointment_date).offset(skip).limit(limit)
    result = await db.execute(query)
    appointments = result.scalars().all()
    return appointments


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific appointment by ID"""
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.patient))
        .where(Appointment.id == appointment_id)
    )
    appointment = result.scalars().first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found"
        )
    return appointment


@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: int,
    appointment_update: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing appointment"""
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.patient))
        .where(Appointment.id == appointment_id)
    )
    appointment = result.scalars().first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found"
        )

    update_data = appointment_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appointment, field, value)

    await db.commit()
    await db.refresh(appointment)
    return appointment


@router.patch("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Cancel an appointment"""
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.patient))
        .where(Appointment.id == appointment_id)
    )
    appointment = result.scalars().first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found"
        )

    if appointment.status in [AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel appointment with status: {appointment.status}"
        )

    appointment.status = AppointmentStatus.CANCELLED

    if appointment.slot_id:
        result = await db.execute(select(Slot).where(Slot.id == appointment.slot_id))
        slot = result.scalars().first()
        if slot:
            slot.is_available = True

    await db.commit()
    await db.refresh(appointment)
    return appointment


@router.patch("/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(
    appointment_id: int,
    new_appointment_date: datetime = Query(..., description="New appointment date and time"),
    new_slot_id: Optional[int] = Query(None, description="New slot ID if using slot-based booking"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Reschedule an appointment to a new date/time"""
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.patient))
        .where(Appointment.id == appointment_id)
    )
    appointment = result.scalars().first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found"
        )

    if appointment.status in [AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reschedule appointment with status: {appointment.status}"
        )

    if appointment.slot_id:
        result = await db.execute(select(Slot).where(Slot.id == appointment.slot_id))
        old_slot = result.scalars().first()
        if old_slot:
            old_slot.is_available = True

    if new_slot_id:
        result = await db.execute(select(Slot).where(Slot.id == new_slot_id))
        new_slot = result.scalars().first()

        if not new_slot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Slot with ID {new_slot_id} not found"
            )

        if not new_slot.is_available or new_slot.is_blocked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected slot is not available"
            )

        new_slot.is_available = False
        appointment.slot_id = new_slot_id

    appointment.appointment_date = new_appointment_date

    await db.commit()
    await db.refresh(appointment)
    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an appointment"""
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalars().first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found"
        )

    if appointment.slot_id:
        result = await db.execute(select(Slot).where(Slot.id == appointment.slot_id))
        slot = result.scalars().first()
        if slot:
            slot.is_available = True

    await db.delete(appointment)
    await db.commit()
    return None
