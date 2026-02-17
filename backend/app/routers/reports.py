from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
from app.database import get_db
from app.mongo_client import get_mongo_db
from app.services.mongo_services import AuditLogService, DailySummaryService
from app.models import (
    User, Patient, Appointment, Visit, Prescription,
    Invoice, Batch, Medicine, AppointmentStatus, InvoiceStatus
)
from app.auth import get_current_active_user

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/daily-summary")
async def get_daily_summary(
    report_date: Optional[date] = Query(None, description="Date for report (default: today)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get today's summary: patients, visits, revenue"""
    if not report_date:
        report_date = date.today()

    start_datetime = datetime.combine(report_date, datetime.min.time())
    end_datetime = datetime.combine(report_date, datetime.max.time())

    result = await db.execute(
        select(func.count(Appointment.id)).where(
            and_(
                Appointment.appointment_date >= start_datetime,
                Appointment.appointment_date <= end_datetime
            )
        )
    )
    total_appointments = result.scalar()

    result = await db.execute(
        select(
            Appointment.status,
            func.count(Appointment.id)
        )
        .where(
            and_(
                Appointment.appointment_date >= start_datetime,
                Appointment.appointment_date <= end_datetime
            )
        )
        .group_by(Appointment.status)
    )
    appointments_by_status = {row[0].value: row[1] for row in result}

    result = await db.execute(
        select(func.count(Visit.id)).where(
            and_(
                Visit.started_at >= start_datetime,
                Visit.started_at <= end_datetime
            )
        )
    )
    total_visits = result.scalar()

    result = await db.execute(
        select(func.count(Prescription.id)).where(
            and_(
                Prescription.created_at >= start_datetime,
                Prescription.created_at <= end_datetime
            )
        )
    )
    total_prescriptions = result.scalar()

    result = await db.execute(
        select(func.count(Prescription.id)).where(
            and_(
                Prescription.created_at >= start_datetime,
                Prescription.created_at <= end_datetime,
                Prescription.is_dispensed == 1
            )
        )
    )
    prescriptions_dispensed = result.scalar()

    result = await db.execute(
        select(
            func.sum(Invoice.total_amount).label('total_revenue'),
            func.sum(Invoice.paid_amount).label('total_paid')
        )
        .where(
            and_(
                Invoice.invoice_date >= start_datetime,
                Invoice.invoice_date <= end_datetime
            )
        )
    )
    revenue_row = result.first()
    total_revenue = revenue_row.total_revenue or Decimal('0')
    total_paid = revenue_row.total_paid or Decimal('0')

    result = await db.execute(
        select(
            Invoice.status,
            func.count(Invoice.id)
        )
        .where(
            and_(
                Invoice.invoice_date >= start_datetime,
                Invoice.invoice_date <= end_datetime
            )
        )
        .group_by(Invoice.status)
    )
    invoices_by_status = {row[0].value: row[1] for row in result}

    return {
        "date": report_date,
        "appointments": {
            "total": total_appointments,
            "by_status": appointments_by_status
        },
        "visits": {
            "total": total_visits
        },
        "prescriptions": {
            "total": total_prescriptions,
            "dispensed": prescriptions_dispensed,
            "pending": total_prescriptions - prescriptions_dispensed
        },
        "revenue": {
            "total_billed": float(total_revenue),
            "total_paid": float(total_paid),
            "pending": float(total_revenue - total_paid)
        },
        "invoices": {
            "by_status": invoices_by_status
        }
    }


@router.get("/appointments")
async def get_appointment_analytics(
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Appointment analytics for date range"""
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    result = await db.execute(
        select(func.count(Appointment.id)).where(
            and_(
                Appointment.appointment_date >= start_datetime,
                Appointment.appointment_date <= end_datetime
            )
        )
    )
    total = result.scalar()

    result = await db.execute(
        select(
            Appointment.status,
            func.count(Appointment.id)
        )
        .where(
            and_(
                Appointment.appointment_date >= start_datetime,
                Appointment.appointment_date <= end_datetime
            )
        )
        .group_by(Appointment.status)
    )
    by_status = {row[0].value: row[1] for row in result}

    result = await db.execute(
        select(
            func.date(Appointment.appointment_date).label('date'),
            func.count(Appointment.id).label('count')
        )
        .where(
            and_(
                Appointment.appointment_date >= start_datetime,
                Appointment.appointment_date <= end_datetime
            )
        )
        .group_by(func.date(Appointment.appointment_date))
        .order_by(func.date(Appointment.appointment_date))
    )
    by_day = [{"date": str(row.date), "count": row.count} for row in result]

    cancelled = by_status.get('cancelled', 0)
    cancellation_rate = (cancelled / total * 100) if total > 0 else 0

    completed = by_status.get('completed', 0)
    completion_rate = (completed / total * 100) if total > 0 else 0

    return {
        "date_range": {
            "start": start_date,
            "end": end_date
        },
        "total_appointments": total,
        "by_status": by_status,
        "by_day": by_day,
        "metrics": {
            "cancellation_rate": round(cancellation_rate, 2),
            "completion_rate": round(completion_rate, 2)
        }
    }


@router.get("/prescriptions")
async def get_prescription_patterns(
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Prescription patterns and analytics"""
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    result = await db.execute(
        select(func.count(Prescription.id)).where(
            and_(
                Prescription.created_at >= start_datetime,
                Prescription.created_at <= end_datetime
            )
        )
    )
    total = result.scalar()

    result = await db.execute(
        select(
            Prescription.is_dispensed,
            func.count(Prescription.id)
        )
        .where(
            and_(
                Prescription.created_at >= start_datetime,
                Prescription.created_at <= end_datetime
            )
        )
        .group_by(Prescription.is_dispensed)
    )
    dispensing_status = {
        "dispensed" if row[0] == 1 else "pending": row[1]
        for row in result
    }

    from app.models import PrescriptionItem
    result = await db.execute(
        select(
            Medicine.name,
            func.count(PrescriptionItem.id).label('prescription_count'),
            func.sum(PrescriptionItem.quantity).label('total_quantity')
        )
        .join(PrescriptionItem, PrescriptionItem.medicine_id == Medicine.id)
        .join(Prescription, Prescription.id == PrescriptionItem.prescription_id)
        .where(
            and_(
                Prescription.created_at >= start_datetime,
                Prescription.created_at <= end_datetime
            )
        )
        .group_by(Medicine.id)
        .order_by(func.count(PrescriptionItem.id).desc())
        .limit(10)
    )
    top_medicines = [
        {
            "medicine": row.name,
            "times_prescribed": row.prescription_count,
            "total_quantity": row.total_quantity
        }
        for row in result
    ]

    return {
        "date_range": {
            "start": start_date,
            "end": end_date
        },
        "total_prescriptions": total,
        "dispensing_status": dispensing_status,
        "top_prescribed_medicines": top_medicines
    }


@router.get("/inventory")
async def get_inventory_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Stock movement and inventory report"""
    result = await db.execute(select(func.count(Medicine.id)))
    total_medicines = result.scalar()

    result = await db.execute(select(func.count(Batch.id)))
    total_batches = result.scalar()

    result = await db.execute(
        select(func.count(Batch.id)).where(Batch.quantity > 0)
    )
    active_batches = result.scalar()

    result = await db.execute(
        select(func.sum(Batch.quantity * Batch.purchase_price)).where(
            Batch.quantity > 0
        )
    )
    total_purchase_value = result.scalar() or 0

    result = await db.execute(
        select(func.sum(Batch.quantity * Batch.sale_price)).where(
            Batch.quantity > 0
        )
    )
    total_sale_value = result.scalar() or 0

    result = await db.execute(
        select(
            Medicine.name,
            func.sum(Batch.quantity).label('total_quantity'),
            Medicine.reorder_level
        )
        .join(Batch, Batch.medicine_id == Medicine.id)
        .where(Batch.quantity > 0)
        .group_by(Medicine.id)
        .having(func.sum(Batch.quantity) < Medicine.reorder_level)
    )
    low_stock_count = len(list(result))

    expiry_threshold = date.today() + timedelta(days=30)
    result = await db.execute(
        select(func.count(Batch.id)).where(
            and_(
                Batch.quantity > 0,
                Batch.expiry_date <= expiry_threshold
            )
        )
    )
    expiring_soon_count = result.scalar()

    return {
        "medicines": {
            "total_in_catalog": total_medicines
        },
        "batches": {
            "total": total_batches,
            "active": active_batches,
            "expired_or_empty": total_batches - active_batches
        },
        "stock_value": {
            "at_purchase_price": float(total_purchase_value),
            "at_sale_price": float(total_sale_value),
            "potential_profit": float(total_sale_value - total_purchase_value)
        },
        "alerts": {
            "low_stock_medicines": low_stock_count,
            "expiring_soon_batches": expiring_soon_count
        }
    }


@router.get("/revenue")
async def get_revenue_report(
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Revenue report for date range"""
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    result = await db.execute(
        select(func.count(Invoice.id)).where(
            and_(
                Invoice.invoice_date >= start_datetime,
                Invoice.invoice_date <= end_datetime
            )
        )
    )
    total_invoices = result.scalar()

    result = await db.execute(
        select(
            func.sum(Invoice.subtotal).label('subtotal'),
            func.sum(Invoice.tax_amount).label('tax'),
            func.sum(Invoice.discount_amount).label('discount'),
            func.sum(Invoice.total_amount).label('total'),
            func.sum(Invoice.paid_amount).label('paid')
        )
        .where(
            and_(
                Invoice.invoice_date >= start_datetime,
                Invoice.invoice_date <= end_datetime
            )
        )
    )
    revenue = result.first()

    result = await db.execute(
        select(
            Invoice.payment_method,
            func.sum(Invoice.paid_amount).label('amount')
        )
        .where(
            and_(
                Invoice.invoice_date >= start_datetime,
                Invoice.invoice_date <= end_datetime,
                Invoice.payment_method.isnot(None)
            )
        )
        .group_by(Invoice.payment_method)
    )
    by_payment_method = {
        row.payment_method: float(row.amount)
        for row in result
    }

    result = await db.execute(
        select(
            func.date(Invoice.invoice_date).label('date'),
            func.sum(Invoice.total_amount).label('revenue'),
            func.sum(Invoice.paid_amount).label('collected')
        )
        .where(
            and_(
                Invoice.invoice_date >= start_datetime,
                Invoice.invoice_date <= end_datetime
            )
        )
        .group_by(func.date(Invoice.invoice_date))
        .order_by(func.date(Invoice.invoice_date))
    )
    daily_revenue = [
        {
            "date": str(row.date),
            "revenue": float(row.revenue),
            "collected": float(row.collected)
        }
        for row in result
    ]

    return {
        "date_range": {
            "start": start_date,
            "end": end_date
        },
        "total_invoices": total_invoices,
        "revenue": {
            "subtotal": float(revenue.subtotal or 0),
            "tax": float(revenue.tax or 0),
            "discount": float(revenue.discount or 0),
            "total": float(revenue.total or 0),
            "paid": float(revenue.paid or 0),
            "outstanding": float((revenue.total or 0) - (revenue.paid or 0))
        },
        "by_payment_method": by_payment_method,
        "daily_breakdown": daily_revenue
    }



@router.get("/audit-logs")
async def get_audit_logs(
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    mongo_db = Depends(get_mongo_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Query audit logs from MongoDB

    Filters:
    - user_id: Filter by user who performed action
    - resource_type: Filter by resource (patient, appointment, prescription, etc.)
    - action: Filter by action type (CREATE, UPDATE, DELETE, VIEW)
    - start_date/end_date: Filter by date range
    - skip/limit: Pagination

    Returns complete audit trail with user, timestamp, resource, and details
    """
    audit_service = AuditLogService(mongo_db)
    logs = await audit_service.get_logs(
        user_id=user_id,
        resource_type=resource_type,
        action=action,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )
    return {
        "total": len(logs),
        "logs": logs
    }


@router.get("/daily-summary-mongo/{summary_date}")
async def get_daily_summary_from_mongo(
    summary_date: date,
    mongo_db = Depends(get_mongo_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get pre-aggregated daily summary from MongoDB (INSTANT!)

    Returns pre-calculated statistics for:
    - Patient stats (new patients, total visits)
    - Appointment stats (scheduled, completed, cancelled)
    - Consultation stats
    - Pharmacy stats (prescriptions dispensed)
    - Revenue stats

    This is 100x faster than calculating from PostgreSQL!
    """
    summary_service = DailySummaryService(mongo_db)
    summary = await summary_service.get_summary(summary_date)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No pre-aggregated summary found for {summary_date}. Summary may not have been generated yet."
        )

    return summary


@router.get("/daily-summaries-range")
async def get_daily_summaries_range(
    start_date: date,
    end_date: date,
    mongo_db = Depends(get_mongo_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get pre-aggregated daily summaries for date range

    Returns array of daily summaries between start and end dates
    Perfect for charts and trend analysis
    """
    summary_service = DailySummaryService(mongo_db)
    summaries = await summary_service.get_summaries_range(
        start_date=start_date,
        end_date=end_date
    )
    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_days": len(summaries),
        "summaries": summaries
    }