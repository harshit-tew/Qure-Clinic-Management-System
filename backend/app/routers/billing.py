from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from decimal import Decimal
from app.database import get_db
from app.models import User, Invoice, InvoiceItem, Patient, Visit, Prescription, PrescriptionItem, Medicine, InvoiceStatus
from app.schemas import InvoiceCreate, InvoiceResponse
from app.auth import get_current_active_user

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def generate_bill(
    invoice: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a new bill/invoice

    AUTO MODE (Recommended): Just provide prescription_id
    - System auto-generates items from prescription (medicines + consultation fee)
    - ONE PRESCRIPTION = ONE BILL (duplicate prevention)

    MANUAL MODE: Provide custom items + (visit_id or patient_id)
    """
    patient_id = None
    visit_id = None
    prescription_id = None
    invoice_items = []

    if invoice.prescription_id:
        result = await db.execute(
            select(Invoice).where(Invoice.prescription_id == invoice.prescription_id)
        )
        existing_invoice = result.scalars().first()

        if existing_invoice:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invoice already exists for prescription ID {invoice.prescription_id}. Invoice ID: {existing_invoice.id}"
            )

        result = await db.execute(
            select(Prescription)
            .options(selectinload(Prescription.items).selectinload(PrescriptionItem.medicine))
            .where(Prescription.id == invoice.prescription_id)
        )
        prescription = result.scalars().first()

        if not prescription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prescription with ID {invoice.prescription_id} not found"
            )

        prescription_id = prescription.id
        visit_id = prescription.visit_id
        patient_id = prescription.patient_id

        invoice_items.append({
            "description": "Consultation Fee",
            "item_type": "consultation",
            "quantity": 1,
            "unit_price": Decimal(str(invoice.consultation_fee)),
            "total_price": Decimal(str(invoice.consultation_fee)),
            "medicine_id": None
        })

        for presc_item in prescription.items:
            medicine = presc_item.medicine
            unit_price = Decimal(str(medicine.unit_price))
            quantity = presc_item.quantity
            total_price = unit_price * quantity

            invoice_items.append({
                "description": f"{medicine.name} {medicine.strength} - {presc_item.dosage}",
                "item_type": "medicine",
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": total_price,
                "medicine_id": medicine.id
            })

    else:
        if not invoice.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide either prescription_id (auto mode) or items (manual mode)"
            )

        if invoice.visit_id:
            result = await db.execute(select(Visit).where(Visit.id == invoice.visit_id))
            visit = result.scalars().first()
            if not visit:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Visit with ID {invoice.visit_id} not found"
                )
            visit_id = visit.id
            patient_id = visit.patient_id

        elif invoice.patient_id:
            result = await db.execute(select(Patient).where(Patient.id == invoice.patient_id))
            patient = result.scalars().first()
            if not patient:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Patient with ID {invoice.patient_id} not found"
                )
            patient_id = patient.id

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide visit_id or patient_id for manual billing"
            )

        invoice_items = [item.model_dump() for item in invoice.items]

    subtotal = sum(Decimal(str(item["total_price"])) for item in invoice_items)
    tax_amount = Decimal("0")
    discount_amount = Decimal("0")
    total_amount = subtotal + tax_amount - discount_amount

    db_invoice = Invoice(
        patient_id=patient_id,
        visit_id=visit_id,
        prescription_id=prescription_id,
        status=InvoiceStatus.PENDING,
        subtotal=subtotal,
        tax_amount=tax_amount,
        discount_amount=discount_amount,
        total_amount=total_amount,
        paid_amount=Decimal("0"),
        payment_method=invoice.payment_method
    )
    db.add(db_invoice)
    await db.flush()

    for item in invoice_items:
        db_item = InvoiceItem(
            invoice_id=db_invoice.id,
            **item
        )
        db.add(db_item)

    await db.commit()
    await db.refresh(db_invoice)

    result = await db.execute(
        select(Invoice)
        .options(
            selectinload(Invoice.items),
            selectinload(Invoice.patient)
        )
        .where(Invoice.id == db_invoice.id)
    )
    invoice_with_items = result.scalars().first()
    return invoice_with_items


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_bill(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get bill details by invoice ID"""
    result = await db.execute(
        select(Invoice)
        .options(
            selectinload(Invoice.items),
            selectinload(Invoice.patient)
        )
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalars().first()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found"
        )

    return invoice


@router.get("/patient/{patient_id}", response_model=List[InvoiceResponse])
async def get_patient_billing_history(
    patient_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get patient's billing history"""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalars().first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found"
        )

    result = await db.execute(
        select(Invoice)
        .options(
            selectinload(Invoice.items),
            selectinload(Invoice.patient)
        )
        .where(Invoice.patient_id == patient_id)
        .order_by(Invoice.invoice_date.desc())
        .offset(skip)
        .limit(limit)
    )
    invoices = result.scalars().all()
    return invoices


@router.post("/prescription/{prescription_id}/pay", response_model=InvoiceResponse)
async def mark_prescription_as_paid(
    prescription_id: int,
    payment_method: str = "cash",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Mark invoice as paid using prescription ID (SIMPLIFIED)

    Just provide prescription_id - system finds invoice and marks as paid with full amount
    """
    result = await db.execute(
        select(Invoice)
        .options(
            selectinload(Invoice.items),
            selectinload(Invoice.patient)
        )
        .where(Invoice.prescription_id == prescription_id)
    )
    invoice = result.scalars().first()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No invoice found for prescription ID {prescription_id}. Please generate invoice first."
        )

    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is already paid"
        )

    invoice.paid_amount = invoice.total_amount
    invoice.payment_method = payment_method
    invoice.status = InvoiceStatus.PAID

    await db.commit()
    await db.refresh(invoice)
    return invoice
