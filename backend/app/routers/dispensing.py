from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import List
from datetime import date, timedelta
from app.database import get_db
from app.mongo_client import get_mongo_db
from app.services.mongo_services import StockMovementService
from app.models import User, Prescription, PrescriptionItem, Batch, Medicine
from app.schemas import PrescriptionResponse
from app.auth import get_current_active_user

router = APIRouter(prefix="/dispensing", tags=["Dispensing"])


@router.get("/pending", response_model=List[PrescriptionResponse])
async def get_pending_prescriptions(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get prescriptions pending dispensing"""
    result = await db.execute(
        select(Prescription)
        .options(
            selectinload(Prescription.items).selectinload(PrescriptionItem.medicine),
            selectinload(Prescription.patient)
        )
        .where(Prescription.is_dispensed == 0)
        .order_by(Prescription.created_at)
        .offset(skip)
        .limit(limit)
    )
    prescriptions = result.scalars().all()
    return prescriptions


@router.post("/{prescription_id}/dispense")
async def dispense_prescription(
    prescription_id: int,
    db: AsyncSession = Depends(get_db),
    mongo_db = Depends(get_mongo_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Dispense medicines for a prescription using FIFO (First In, First Out).
    Deducts from oldest batches first, skipping expired or soon-to-expire batches.
    """
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
            detail="Prescription has already been dispensed"
        )

    result = await db.execute(
        select(PrescriptionItem).where(PrescriptionItem.prescription_id == prescription_id)
    )
    items = result.scalars().all()

    dispensing_log = []
    expiry_threshold = date.today() + timedelta(days=30)

    for item in items:
        quantity_needed = item.quantity
        medicine_id = item.medicine_id

        result = await db.execute(
            select(Batch)
            .where(
                and_(
                    Batch.medicine_id == medicine_id,
                    Batch.quantity > 0,
                    Batch.expiry_date > expiry_threshold
                )
            )
            .order_by(Batch.expiry_date)
        )
        batches = result.scalars().all()

        if not batches:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No available stock for medicine ID {medicine_id}"
            )

        total_available = sum(batch.quantity for batch in batches)
        if total_available < quantity_needed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for medicine ID {medicine_id}. Need: {quantity_needed}, Available: {total_available}"
            )

        remaining_quantity = quantity_needed
        batches_used = []

        for batch in batches:
            if remaining_quantity <= 0:
                break

            quantity_from_batch = min(batch.quantity, remaining_quantity)
            batch.quantity -= quantity_from_batch
            remaining_quantity -= quantity_from_batch

            batches_used.append({
                "batch_id": batch.id,
                "batch_number": batch.batch_number,
                "quantity_dispensed": quantity_from_batch,
                "expiry_date": batch.expiry_date
            })

        dispensing_log.append({
            "medicine_id": medicine_id,
            "quantity_requested": quantity_needed,
            "batches_used": batches_used
        })

    prescription.is_dispensed = 1
    prescription.dispensed_by = current_user.id
    from datetime import datetime
    prescription.dispensed_at = datetime.utcnow()

    try:
        stock_service = StockMovementService(mongo_db)

        for item_log in dispensing_log:
            medicine_result = await db.execute(
                select(Medicine).where(Medicine.id == item_log["medicine_id"])
            )
            medicine = medicine_result.scalars().first()

            for batch_used in item_log["batches_used"]:
                await stock_service.log_stock_out(
                    medicine_id=medicine.id if medicine else item_log["medicine_id"],
                    medicine_name=medicine.name if medicine else "Unknown",
                    batch_id=batch_used["batch_id"],
                    batch_number=batch_used["batch_number"],
                    quantity=batch_used["quantity_dispensed"],
                    reason="DISPENSED",
                    reference_type="prescription",
                    reference_id=prescription_id,
                    performed_by_id=current_user.id,
                    performed_by_name=current_user.full_name
                )
    except Exception as e:
        print(f"MongoDB stock movement log failed: {e}")

    await db.commit()

    return {
        "message": "Prescription dispensed successfully",
        "prescription_id": prescription_id,
        "dispensed_by": current_user.full_name,
        "dispensing_details": dispensing_log
    }


@router.get("/{prescription_id}/details")
async def get_dispensing_details(
    prescription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get dispensing details for a prescription"""
    result = await db.execute(
        select(Prescription).where(Prescription.id == prescription_id)
    )
    prescription = result.scalars().first()

    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription with ID {prescription_id} not found"
        )

    if not prescription.is_dispensed:
        return {
            "message": "Prescription not yet dispensed",
            "is_dispensed": False
        }

    result = await db.execute(
        select(User).where(User.id == prescription.dispensed_by)
    )
    dispenser = result.scalars().first()

    return {
        "prescription_id": prescription.id,
        "is_dispensed": True,
        "dispensed_at": prescription.dispensed_at,
        "dispensed_by": {
            "id": dispenser.id if dispenser else None,
            "name": dispenser.full_name if dispenser else "Unknown"
        }
    }


@router.post("/{prescription_id}/return")
async def return_medicines(
    prescription_id: int,
    medicine_id: int,
    quantity: int,
    reason: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Handle medicine returns.
    In a real system, this would add stock back to a specific batch
    or create a new 'returned' batch.
    """
    result = await db.execute(
        select(Prescription).where(Prescription.id == prescription_id)
    )
    prescription = result.scalars().first()

    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription with ID {prescription_id} not found"
        )

    if not prescription.is_dispensed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot return medicines from a prescription that wasn't dispensed"
        )

    result = await db.execute(
        select(PrescriptionItem).where(
            and_(
                PrescriptionItem.prescription_id == prescription_id,
                PrescriptionItem.medicine_id == medicine_id
            )
        )
    )
    item = result.scalars().first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found in this prescription"
        )

    if quantity > item.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot return more than dispensed. Dispensed: {item.quantity}"
        )

    return {
        "message": "Return processed successfully",
        "prescription_id": prescription_id,
        "medicine_id": medicine_id,
        "quantity_returned": quantity,
        "reason": reason,
        "processed_by": current_user.full_name,
        "note": "In production, this would update inventory and create audit log"
    }


@router.get("/low-stock-alert")
async def check_low_stock_for_pending(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Check if pending prescriptions can be fulfilled with current stock.
    Alert for medicines that are low in stock.
    """
    result = await db.execute(
        select(Prescription).where(Prescription.is_dispensed == 0)
    )
    pending_prescriptions = result.scalars().all()

    alerts = []

    for prescription in pending_prescriptions:
        result = await db.execute(
            select(PrescriptionItem).where(
                PrescriptionItem.prescription_id == prescription.id
            )
        )
        items = result.scalars().all()

        for item in items:
            result = await db.execute(
                select(Batch).where(
                    and_(
                        Batch.medicine_id == item.medicine_id,
                        Batch.quantity > 0
                    )
                )
            )
            batches = result.scalars().all()
            total_available = sum(batch.quantity for batch in batches)

            result = await db.execute(
                select(Medicine).where(Medicine.id == item.medicine_id)
            )
            medicine = result.scalars().first()

            if total_available < item.quantity:
                alerts.append({
                    "prescription_id": prescription.id,
                    "medicine_id": item.medicine_id,
                    "medicine_name": medicine.name if medicine else "Unknown",
                    "required": item.quantity,
                    "available": total_available,
                    "shortage": item.quantity - total_available
                })

    return {
        "total_pending_prescriptions": len(pending_prescriptions),
        "alerts": alerts,
        "alert_count": len(alerts)
    }