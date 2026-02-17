from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.models import Medicine, User
from app.schemas import MedicineCreate, MedicineUpdate, MedicineResponse
from app.auth import get_current_active_user

router = APIRouter(prefix="/medicines", tags=["Medicines"])


@router.post("", response_model=MedicineResponse, status_code=status.HTTP_201_CREATED)
async def create_medicine(
    medicine: MedicineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    
    db_medicine = Medicine(**medicine.model_dump())
    db.add(db_medicine)
    await db.commit()
    await db.refresh(db_medicine)
    return db_medicine


@router.get("", response_model=List[MedicineResponse])
async def get_medicines(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Medicine).offset(skip).limit(limit))
    medicines = result.scalars().all()
    return medicines


@router.get("/low-stock", response_model=List[MedicineResponse])
async def get_low_stock_medicines(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(
        select(Medicine).where(Medicine.stock_quantity <= Medicine.reorder_level)
    )
    medicines = result.scalars().all()
    return medicines


@router.get("/{medicine_id}", response_model=MedicineResponse)
async def get_medicine(
    medicine_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific medicine by ID"""
    result = await db.execute(select(Medicine).where(Medicine.id == medicine_id))
    medicine = result.scalars().first()

    if not medicine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with ID {medicine_id} not found"
        )
    return medicine


@router.put("/{medicine_id}", response_model=MedicineResponse)
async def update_medicine(
    medicine_id: int,
    medicine_update: MedicineUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing medicine"""
    result = await db.execute(select(Medicine).where(Medicine.id == medicine_id))
    medicine = result.scalars().first()

    if not medicine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with ID {medicine_id} not found"
        )

    update_data = medicine_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(medicine, field, value)

    await db.commit()
    await db.refresh(medicine)
    return medicine


@router.delete("/{medicine_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medicine(
    medicine_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a medicine"""
    result = await db.execute(select(Medicine).where(Medicine.id == medicine_id))
    medicine = result.scalars().first()

    if not medicine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with ID {medicine_id} not found"
        )

    await db.delete(medicine)
    await db.commit()
    return None


@router.post("/{medicine_id}/add-stock", response_model=MedicineResponse)
async def add_stock(
    medicine_id: int,
    quantity: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add stock to a medicine"""
    result = await db.execute(select(Medicine).where(Medicine.id == medicine_id))
    medicine = result.scalars().first()

    if not medicine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with ID {medicine_id} not found"
        )

    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than 0"
        )

    medicine.stock_quantity += quantity
    await db.commit()
    await db.refresh(medicine)
    return medicine


@router.get("/search/by-name", response_model=List[MedicineResponse])
async def search_medicines_by_name(
    name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Search medicines by name"""
    result = await db.execute(
        select(Medicine).where(Medicine.name.ilike(f"%{name}%"))
    )
    medicines = result.scalars().all()
    return medicines