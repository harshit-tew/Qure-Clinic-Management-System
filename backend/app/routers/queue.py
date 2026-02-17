from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis
from datetime import date, datetime
from typing import List

from app.database import get_db
from app.redis_client import get_redis
from app.services.queue_service import QueueService
from app.models import User, Appointment, Patient, AppointmentStatus
from app.schemas import (
    QueueTokenResponse,
    QueueCheckInRequest,
    QueueWalkInRequest,
    QueueStatusUpdate,
    QueueSummaryResponse
)
from app.auth import get_current_active_user

router = APIRouter(prefix="/queue", tags=["Queue Management"])


@router.post("/checkin/{appointment_id}", response_model=QueueTokenResponse)
async def check_in_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalars().first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found"
        )

    today = date.today()
    appointment_date = appointment.appointment_date.date()

    if appointment_date != today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Appointment is for {appointment_date}, not today ({today})"
        )

    if appointment.status == AppointmentStatus.CHECKED_IN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment already checked in"
        )

    result = await db.execute(
        select(Patient).where(Patient.id == appointment.patient_id)
    )
    patient = result.scalars().first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {appointment.patient_id} not found"
        )

    queue_service = QueueService(redis)
    token_data = await queue_service.check_in(
        queue_date=today,
        patient_id=patient.id,
        patient_name=patient.name,
        appointment_id=appointment.id,
        is_walk_in=False,
        chief_complaint=appointment.chief_complaint
    )

    appointment.status = AppointmentStatus.CHECKED_IN
    await db.commit()

    return QueueTokenResponse(
        token_number=token_data["token_number"],
        patient_id=token_data["patient_id"],
        patient_name=token_data["patient_name"],
        appointment_id=token_data["appointment_id"],
        status=token_data["status"],
        checkin_time=datetime.fromisoformat(token_data["checkin_time"]),
        is_walk_in=False
    )


@router.post("/walk-in", response_model=QueueTokenResponse)
async def add_walk_in_patient(
    walk_in: QueueWalkInRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(
        select(Patient).where(Patient.id == walk_in.patient_id)
    )
    patient = result.scalars().first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {walk_in.patient_id} not found"
        )

    today = date.today()
    queue_service = QueueService(redis)
    token_data = await queue_service.check_in(
        queue_date=today,
        patient_id=patient.id,
        patient_name=patient.name,
        appointment_id=None,
        is_walk_in=True,
        chief_complaint=walk_in.chief_complaint
    )

    return QueueTokenResponse(
        token_number=token_data["token_number"],
        patient_id=token_data["patient_id"],
        patient_name=token_data["patient_name"],
        appointment_id=None,
        status=token_data["status"],
        checkin_time=datetime.fromisoformat(token_data["checkin_time"]),
        is_walk_in=True
    )



@router.get("/today", response_model=QueueSummaryResponse)
async def get_today_queue(
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_active_user)
):

    today = date.today()
    queue_service = QueueService(redis)
    summary = await queue_service.get_queue_summary(today)

    tokens = []
    for token in summary["tokens"]:
        tokens.append(QueueTokenResponse(
            token_number=token["token_number"],
            patient_id=token["patient_id"],
            patient_name=token["patient_name"],
            appointment_id=token.get("appointment_id"),
            status=token["status"],
            checkin_time=datetime.fromisoformat(token["checkin_time"]),
            called_time=datetime.fromisoformat(token["called_time"]) if token.get("called_time") else None,
            completed_time=datetime.fromisoformat(token["completed_time"]) if token.get("completed_time") else None,
            is_walk_in=token.get("is_walk_in", False)
        ))

    return QueueSummaryResponse(
        date=today,
        total_tokens=summary["total_tokens"],
        checked_in=summary["checked_in"],
        waiting=summary["waiting"],
        with_doctor=summary["with_doctor"],
        completed=summary["completed"],
        skipped=summary["skipped"],
        no_show=summary["no_show"],
        current_token=summary["current_token"],
        tokens=tokens
    )


@router.get("/current")
async def get_current_serving(
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_active_user)
):
    today = date.today()
    queue_service = QueueService(redis)
    current_token = await queue_service.get_current_serving(today)

    if current_token is None:
        return {
            "current_token": None,
            "message": "No patient currently being served"
        }

    tokens = await queue_service.get_today_queue(today)
    token_data = next((t for t in tokens if t["token_number"] == current_token), None)

    return {
        "current_token": current_token,
        "patient_name": token_data["patient_name"] if token_data else None,
        "status": "WITH_DOCTOR"
    }

@router.post("/next", response_model=QueueTokenResponse)
async def call_next_patient(
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Call next waiting patient

    - Finds first patient with WAITING status
    - Marks as WITH_DOCTOR
    - Updates appointment status if applicable
    - Returns token data
    """
    today = date.today()
    queue_service = QueueService(redis)
    token_data = await queue_service.call_next_patient(today)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No patients waiting in queue"
        )

    if token_data.get("appointment_id"):
        result = await db.execute(
            select(Appointment).where(Appointment.id == token_data["appointment_id"])
        )
        appointment = result.scalars().first()
        if appointment:
            appointment.status = AppointmentStatus.WITH_DOCTOR
            await db.commit()

    return QueueTokenResponse(
        token_number=token_data["token_number"],
        patient_id=token_data["patient_id"],
        patient_name=token_data["patient_name"],
        appointment_id=token_data.get("appointment_id"),
        status=token_data["status"],
        checkin_time=datetime.fromisoformat(token_data["checkin_time"]),
        called_time=datetime.fromisoformat(token_data["called_time"]) if token_data.get("called_time") else None,
        is_walk_in=token_data.get("is_walk_in", False)
    )


@router.patch("/{token_number}/status", response_model=QueueTokenResponse)
async def update_token_status(
    token_number: int,
    status_update: QueueStatusUpdate,
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    - WAITING: Patient wai ting to be called
    - WITH_DOCTOR: Currently  being seen
    - COMPLETED: Consultation finished
    - SKIPPED: Called bu t not present
    - NO_SHOW: Never show ed up
    """
    today = date.today()
    queue_service = QueueService(redis)
    token_data = await queue_service.update_status(
        today,
        token_number,
        status_update.status
    )

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token {token_number} not found in today's queue"
        )

    if token_data.get("appointment_id"):
        result = await db.execute(
            select(Appointment).where(Appointment.id == token_data["appointment_id"])
        )
        appointment = result.scalars().first()
        if appointment:
            if status_update.status == "WITH_DOCTOR":
                appointment.status = AppointmentStatus.WITH_DOCTOR
            elif status_update.status == "COMPLETED":
                appointment.status = AppointmentStatus.COMPLETED
            elif status_update.status == "NO_SHOW":
                appointment.status = AppointmentStatus.CANCELLED
            await db.commit()

    return QueueTokenResponse(
        token_number=token_data["token_number"],
        patient_id=token_data["patient_id"],
        patient_name=token_data["patient_name"],
        appointment_id=token_data.get("appointment_id"),
        status=token_data["status"],
        checkin_time=datetime.fromisoformat(token_data["checkin_time"]),
        called_time=datetime.fromisoformat(token_data["called_time"]) if token_data.get("called_time") else None,
        completed_time=datetime.fromisoformat(token_data["completed_time"]) if token_data.get("completed_time") else None,
        is_walk_in=token_data.get("is_walk_in", False)
    )


@router.post("/skip/{token_number}", response_model=QueueTokenResponse)
async def skip_patient(
    token_number: int,
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_active_user)
):
    today = date.today()
    queue_service = QueueService(redis)
    token_data = await queue_service.skip_patient(today, token_number)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token {token_number} not found in today's queue"
        )

    return QueueTokenResponse(
        token_number=token_data["token_number"],
        patient_id=token_data["patient_id"],
        patient_name=token_data["patient_name"],
        appointment_id=token_data.get("appointment_id"),
        status=token_data["status"],
        checkin_time=datetime.fromisoformat(token_data["checkin_time"]),
        called_time=datetime.fromisoformat(token_data["called_time"]) if token_data.get("called_time") else None,
        is_walk_in=token_data.get("is_walk_in", False)
    )