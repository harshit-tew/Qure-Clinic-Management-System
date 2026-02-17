from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import date, time, datetime, timedelta
from pydantic import BaseModel, Field
from app.database import get_db
from app.models import User, Slot, SlotBlock, SlotType
from app.schemas import SlotCreate, SlotUpdate, SlotResponse, SlotBlockCreate, SlotBlockResponse
from app.auth import get_current_active_user

router = APIRouter(prefix="/slots", tags=["Slots"])


class BulkSlotCreate(BaseModel):
    slot_date: date
    start_time: str = Field(..., description="Start time in HH:MM format (e.g., '09:00')")
    end_time: str = Field(..., description="End time in HH:MM format (e.g., '17:00')")
    duration_minutes: int = Field(30, ge=15, le=120, description="Duration of each slot in minutes")
    slot_type: SlotType = SlotType.REGULAR


@router.get("", response_model=List[SlotResponse])
async def get_available_slots(
    slot_date: date = Query(..., description="Date to check slots for"),
    slot_type: Optional[SlotType] = Query(None, description="Filter by slot type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get available slots for a specific date"""
    query = select(Slot).where(
        Slot.slot_date == slot_date,
        Slot.is_available.is_(True),
        Slot.is_blocked.is_(False)
    )

    if slot_type:
        query = query.where(Slot.slot_type == slot_type)

    query = query.order_by(Slot.slot_time)
    result = await db.execute(query)
    slots = result.scalars().all()
    return slots


@router.post("", response_model=SlotResponse, status_code=status.HTTP_201_CREATED)
async def create_slot(
    slot: SlotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new slot (admin only)"""
    result = await db.execute(
        select(Slot).where(
            Slot.slot_date == slot.slot_date,
            Slot.slot_time == slot.slot_time
        )
    )
    existing_slot = result.scalars().first()

    if existing_slot:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slot already exists at this date and time"
        )

    db_slot = Slot(**slot.model_dump())
    db.add(db_slot)
    await db.commit()
    await db.refresh(db_slot)
    return db_slot


@router.post("/bulk-create", response_model=List[SlotResponse], status_code=status.HTTP_201_CREATED)
async def bulk_create_slots(
    bulk_data: BulkSlotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    try:
        start_hour, start_min = map(int, bulk_data.start_time.split(':'))
        end_hour, end_min = map(int, bulk_data.end_time.split(':'))
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid time format. Use HH:MM format (e.g., '09:00')"
        )

    start_dt = datetime.combine(bulk_data.slot_date, time(start_hour, start_min))
    end_dt = datetime.combine(bulk_data.slot_date, time(end_hour, end_min))

    if start_dt >= end_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time must be before end time"
        )

    created_slots = []
    current_dt = start_dt
    duration = timedelta(minutes=bulk_data.duration_minutes)

    while current_dt < end_dt:
        slot_time = current_dt.time()

        result = await db.execute(
            select(Slot).where(
                Slot.slot_date == bulk_data.slot_date,
                Slot.slot_time == slot_time
            )
        )
        existing_slot = result.scalars().first()

        if not existing_slot:
            new_slot = Slot(
                slot_date=bulk_data.slot_date,
                slot_time=slot_time,
                duration_minutes=bulk_data.duration_minutes,
                slot_type=bulk_data.slot_type,
                is_available=True,
                is_blocked=False
            )
            db.add(new_slot)
            created_slots.append(new_slot)

        current_dt += duration

    if not created_slots:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No new slots created. All slots in this range already exist."
        )

    await db.commit()

    for slot in created_slots:
        await db.refresh(slot)

    return created_slots


@router.patch("/{slot_id}", response_model=SlotResponse)
async def update_slot(
    slot_id: int,
    slot_update: SlotUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Slot).where(Slot.id == slot_id))
    slot = result.scalars().first()

    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slot with ID {slot_id} not found"
        )

    update_data = slot_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(slot, field):
            setattr(slot, field, value)

    await db.commit()
    await db.refresh(slot)
    return slot


@router.post("/block", response_model=SlotBlockResponse, status_code=status.HTTP_201_CREATED)
async def block_slots(
    slot_block: SlotBlockCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Block slots for a time range (doctor unavailable)"""
    db_block = SlotBlock(**slot_block.model_dump())
    db.add(db_block)

    result = await db.execute(
        select(Slot).where(Slot.slot_date == slot_block.block_date)
    )
    all_slots = result.scalars().all()

    slots_to_block = []
    for slot in all_slots:
        slot_start_dt = datetime.combine(slot.slot_date, slot.slot_time)
        slot_end_dt = slot_start_dt + timedelta(minutes=slot.duration_minutes)
        slot_end_time = slot_end_dt.time()

        overlaps = (
            slot.slot_time < slot_block.end_time and
            slot_end_time > slot_block.start_time
        )

        if overlaps:
            slot.is_blocked = True
            slot.is_available = False
            slot.blocked_reason = slot_block.reason
            slots_to_block.append(slot)

    await db.commit()
    await db.refresh(db_block)
    return db_block


@router.get("/block", response_model=List[SlotBlockResponse])
async def get_slot_blocks(
    block_date: Optional[date] = Query(None, description="Filter by date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all slot blocks"""
    query = select(SlotBlock)

    if block_date:
        query = query.where(SlotBlock.block_date == block_date)

    query = query.order_by(SlotBlock.block_date, SlotBlock.start_time)
    result = await db.execute(query)
    blocks = result.scalars().all()
    return blocks


@router.delete("/block/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unblock_slots(
    block_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove a slot block and unblock the slots"""
    result = await db.execute(select(SlotBlock).where(SlotBlock.id == block_id))
    slot_block = result.scalars().first()

    if not slot_block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slot block with ID {block_id} not found"
        )

    result = await db.execute(
        select(Slot).where(Slot.slot_date == slot_block.block_date)
    )
    all_slots = result.scalars().all()

    for slot in all_slots:
        slot_start_dt = datetime.combine(slot.slot_date, slot.slot_time)
        slot_end_dt = slot_start_dt + timedelta(minutes=slot.duration_minutes)
        slot_end_time = slot_end_dt.time()

        overlaps = (
            slot.slot_time < slot_block.end_time and
            slot_end_time > slot_block.start_time
        )

        if overlaps:
            slot.is_blocked = False
            slot.is_available = True
            slot.blocked_reason = None

    await db.delete(slot_block)
    await db.commit()
    return None