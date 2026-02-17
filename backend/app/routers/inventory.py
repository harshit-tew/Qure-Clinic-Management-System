from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List
from datetime import date, timedelta
from app.database import get_db
from app.mongo_client import get_mongo_db
from app.services.mongo_services import StockMovementService
from app.models import User, Medicine, Batch
from app.schemas import (
    MedicineCreate,
    MedicineUpdate,
    MedicineResponse,
    BatchCreate,
    BatchUpdate,
    BatchResponse
)
from app.auth import get_current_active_user

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post("/medicines", response_model=MedicineResponse, status_code=status.HTTP_201_CREATED)
async def add_medicine(
    medicine: MedicineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_medicine = Medicine(**medicine.model_dump())
    db.add(db_medicine)
    await db.commit()
    await db.refresh(db_medicine)
    return db_medicine


@router.get("/medicines", response_model=List[MedicineResponse])
async def list_medicines(
    search: str = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List/search medicines"""
    query = select(Medicine)

    if search:
        query = query.where(
            (Medicine.name.ilike(f"%{search}%")) |
            (Medicine.generic_name.ilike(f"%{search}%"))
        )

    query = query.offset(skip).limit(limit).order_by(Medicine.name)
    result = await db.execute(query)
    medicines = result.scalars().all()
    return medicines


@router.get("/medicines/{medicine_id}", response_model=MedicineResponse)
async def get_medicine(
    medicine_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get medicine details"""
    result = await db.execute(select(Medicine).where(Medicine.id == medicine_id))
    medicine = result.scalars().first()

    if not medicine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with ID {medicine_id} not found"
        )

    return medicine


@router.patch("/medicines/{medicine_id}", response_model=MedicineResponse)
async def update_medicine(
    medicine_id: int,
    medicine_update: MedicineUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update medicine details (admin only)"""
    result = await db.execute(select(Medicine).where(Medicine.id == medicine_id))
    medicine = result.scalars().first()

    if not medicine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with ID {medicine_id} not found"
        )

    update_data = medicine_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(medicine, field):
            setattr(medicine, field, value)

    await db.commit()
    await db.refresh(medicine)
    return medicine


@router.get("/medicines/{medicine_id}/stock", response_model=List[BatchResponse])
async def get_medicine_stock(
    medicine_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get current stock with batch details"""
    result = await db.execute(select(Medicine).where(Medicine.id == medicine_id))
    medicine = result.scalars().first()

    if not medicine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with ID {medicine_id} not found"
        )

    result = await db.execute(
        select(Batch)
        .where(Batch.medicine_id == medicine_id, Batch.quantity > 0)
        .order_by(Batch.expiry_date)
    )
    batches = result.scalars().all()
    return batches


@router.post("/stock-in", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
async def add_stock(
    batch: BatchCreate,
    db: AsyncSession = Depends(get_db),
    mongo_db = Depends(get_mongo_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add stock (purchase entry) with MongoDB movement logging"""
    result = await db.execute(select(Medicine).where(Medicine.id == batch.medicine_id))
    medicine = result.scalars().first()

    if not medicine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with ID {batch.medicine_id} not found"
        )

    result = await db.execute(
        select(Batch).where(Batch.batch_number == batch.batch_number)
    )
    existing_batch = result.scalars().first()

    if existing_batch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch number {batch.batch_number} already exists"
        )

    db_batch = Batch(**batch.model_dump())
    db.add(db_batch)
    await db.commit()
    await db.refresh(db_batch)

    try:
        stock_service = StockMovementService(mongo_db)
        await stock_service.log_stock_in(
            medicine_id=medicine.id,
            medicine_name=medicine.name,
            batch_id=db_batch.id,
            batch_number=db_batch.batch_number,
            quantity=db_batch.quantity,
            purchase_price=float(db_batch.purchase_price),
            sale_price=float(db_batch.sale_price),
            expiry_date=db_batch.expiry_date,
            supplier=db_batch.supplier or "Unknown",
            performed_by_id=current_user.id,
            performed_by_name=current_user.full_name
        )
    except Exception as e:
        print(f"MongoDB stock movement log failed: {e}")

    return db_batch


@router.get("/stock-in", response_model=List[BatchResponse])
async def get_stock_in_history(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get stock-in history"""
    result = await db.execute(
        select(Batch)
        .order_by(Batch.received_date.desc())
        .offset(skip)
        .limit(limit)
    )
    batches = result.scalars().all()
    return batches


@router.get("/current")
async def get_current_stock(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get current stock levels for all medicines"""
    query = (
        select(
            Medicine.id,
            Medicine.name,
            Medicine.generic_name,
            func.sum(Batch.quantity).label("total_quantity"),
            Medicine.reorder_level
        )
        .join(Batch, Batch.medicine_id == Medicine.id)
        .where(Batch.quantity > 0)
        .group_by(Medicine.id)
        .order_by(Medicine.name)
    )

    result = await db.execute(query)
    stock_levels = []

    for row in result:
        stock_levels.append({
            "medicine_id": row.id,
            "name": row.name,
            "generic_name": row.generic_name,
            "total_quantity": row.total_quantity or 0,
            "reorder_level": row.reorder_level,
            "needs_reorder": (row.total_quantity or 0) < row.reorder_level
        })

    return stock_levels


@router.get("/low-stock")
async def get_low_stock(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get medicines below reorder threshold"""
    query = (
        select(
            Medicine.id,
            Medicine.name,
            Medicine.generic_name,
            func.sum(Batch.quantity).label("total_quantity"),
            Medicine.reorder_level
        )
        .join(Batch, Batch.medicine_id == Medicine.id)
        .where(Batch.quantity > 0)
        .group_by(Medicine.id)
        .having(func.sum(Batch.quantity) < Medicine.reorder_level)
        .order_by(func.sum(Batch.quantity))
    )

    result = await db.execute(query)
    low_stock = []

    for row in result:
        low_stock.append({
            "medicine_id": row.id,
            "name": row.name,
            "generic_name": row.generic_name,
            "current_quantity": row.total_quantity or 0,
            "reorder_level": row.reorder_level,
            "shortage": row.reorder_level - (row.total_quantity or 0)
        })

    return low_stock


@router.get("/expiring")
async def get_expiring_medicines(
    days: int = 90,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get batches expiring within specified days"""
    expiry_threshold = date.today() + timedelta(days=days)

    result = await db.execute(
        select(Batch)
        .options(selectinload(Batch.medicine))
        .where(
            Batch.expiry_date <= expiry_threshold,
            Batch.quantity > 0
        )
        .order_by(Batch.expiry_date)
    )
    expiring_batches = result.scalars().all()

    return [
        {
            "batch_id": batch.id,
            "batch_number": batch.batch_number,
            "medicine_id": batch.medicine_id,
            "medicine_name": batch.medicine.name,
            "quantity": batch.quantity,
            "expiry_date": batch.expiry_date,
            "days_until_expiry": (batch.expiry_date - date.today()).days
        }
        for batch in expiring_batches
    ]


@router.get("/batch/{batch_id}", response_model=BatchResponse)
async def get_batch_details(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get batch details"""
    result = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = result.scalars().first()

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch with ID {batch_id} not found"
        )

    return batch


@router.patch("/batch/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: int,
    batch_update: BatchUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update batch details"""
    result = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = result.scalars().first()

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch with ID {batch_id} not found"
        )

    update_data = batch_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(batch, field):
            setattr(batch, field, value)

    await db.commit()
    await db.refresh(batch)
    return batch


@router.get("/movements")
async def get_stock_movements(
    medicine_id: int = None,
    movement_type: str = None,
    skip: int = 0,
    limit: int = 100,
    mongo_db = Depends(get_mongo_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Query stock movement history from MongoDB

    Filters:
    - medicine_id: Filter by specific medicine
    - movement_type: "IN" or "OUT"
    - skip/limit: Pagination

    Returns complete audit trail of all stock movements
    """
    stock_service = StockMovementService(mongo_db)
    movements = await stock_service.get_movements(
        medicine_id=medicine_id,
        movement_type=movement_type,
        skip=skip,
        limit=limit
    )
    return {
        "total": len(movements),
        "movements": movements
    }