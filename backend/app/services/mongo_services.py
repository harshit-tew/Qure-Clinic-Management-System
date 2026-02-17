from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, date
from typing import List, Dict, Optional
from bson import ObjectId


class VisitHistoryService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.visit_history

    async def create_visit_document(
        self,
        visit_id: int,
        patient_id: int,
        patient_name: str,
        doctor_id: int,
        doctor_name: str,
        visit_date: datetime,
        vitals: Dict,
        chief_complaint: str,
        diagnosis: str,
        treatment_plan: str,
        prescriptions: List[Dict]
    ) -> str:
        document = {
            "visit_id": visit_id,
            "patient": {
                "id": patient_id,
                "name": patient_name
            },
            "doctor": {
                "id": doctor_id,
                "name": doctor_name
            },
            "visit_date": visit_date,
            "vitals": vitals,
            "chief_complaint": chief_complaint,
            "diagnosis": diagnosis,
            "treatment_plan": treatment_plan,
            "prescriptions": prescriptions,
            "created_at": datetime.utcnow()
        }

        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def get_patient_history(
        self,
        patient_id: int,
        limit: int = 10,
        skip: int = 0
    ) -> List[Dict]:
        cursor = self.collection.find(
            {"patient.id": patient_id}
        ).sort("visit_date", -1).skip(skip).limit(limit)

        visits = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            visits.append(doc)

        return visits

    async def get_visit_by_id(self, visit_id: int) -> Optional[Dict]:
        doc = await self.collection.find_one({"visit_id": visit_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc


class AuditLogService:

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.audit_logs

    async def log_action(
        self,
        user_id: int,
        username: str,
        action: str,
        resource_type: str,
        resource_id: int,
        details: Dict,
        ip_address: Optional[str] = None
    ) -> str:
        log = {
            "user": {
                "id": user_id,
                "username": username
            },
            "action": action,
            "resource": {
                "type": resource_type,
                "id": resource_id
            },
            "details": details,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow()
        }

        result = await self.collection.insert_one(log)
        return str(result.inserted_id)

    async def get_logs(
        self,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict]:
        query = {}

        if user_id:
            query["user.id"] = user_id
        if resource_type:
            query["resource.type"] = resource_type
        if action:
            query["action"] = action
        if start_date or end_date:
            query["timestamp"] = {}
            if start_date:
                query["timestamp"]["$gte"] = start_date
            if end_date:
                query["timestamp"]["$lte"] = end_date

        cursor = self.collection.find(query).sort(
            "timestamp", -1
        ).skip(skip).limit(limit)

        logs = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            logs.append(doc)

        return logs


class StockMovementService:

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.stock_movements

    async def log_stock_in(
        self,
        medicine_id: int,
        medicine_name: str,
        batch_id: int,
        batch_number: str,
        quantity: int,
        purchase_price: float,
        sale_price: float,
        expiry_date: date,
        supplier: str,
        performed_by_id: int,
        performed_by_name: str
    ) -> str:
        movement = {
            "movement_type": "IN",
            "medicine": {
                "id": medicine_id,
                "name": medicine_name
            },
            "batch": {
                "id": batch_id,
                "batch_number": batch_number
            },
            "quantity": quantity,
            "purchase_price": purchase_price,
            "sale_price": sale_price,
            "expiry_date": expiry_date,
            "supplier": supplier,
            "performed_by": {
                "id": performed_by_id,
                "name": performed_by_name
            },
            "timestamp": datetime.utcnow()
        }

        result = await self.collection.insert_one(movement)
        return str(result.inserted_id)

    async def log_stock_out(
        self,
        medicine_id: int,
        medicine_name: str,
        batch_id: int,
        batch_number: str,
        quantity: int,
        reason: str,
        reference_type: str,
        reference_id: int,
        performed_by_id: int,
        performed_by_name: str
    ) -> str:
        movement = {
            "movement_type": "OUT",
            "medicine": {
                "id": medicine_id,
                "name": medicine_name
            },
            "batch": {
                "id": batch_id,
                "batch_number": batch_number
            },
            "quantity": quantity,
            "reason": reason,
            "reference": {
                "type": reference_type,
                "id": reference_id
            },
            "performed_by": {
                "id": performed_by_id,
                "name": performed_by_name
            },
            "timestamp": datetime.utcnow()
        }

        result = await self.collection.insert_one(movement)
        return str(result.inserted_id)

    async def get_movements(
        self,
        medicine_id: Optional[int] = None,
        movement_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict]:
        query = {}

        if medicine_id:
            query["medicine.id"] = medicine_id
        if movement_type:
            query["movement_type"] = movement_type
        if start_date or end_date:
            query["timestamp"] = {}
            if start_date:
                query["timestamp"]["$gte"] = start_date
            if end_date:
                query["timestamp"]["$lte"] = end_date

        cursor = self.collection.find(query).sort(
            "timestamp", -1
        ).skip(skip).limit(limit)

        movements = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            movements.append(doc)

        return movements


class DailySummaryService:

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.daily_summaries

    async def create_summary(
        self,
        summary_date: date,
        patient_stats: Dict,
        appointment_stats: Dict,
        consultation_stats: Dict,
        pharmacy_stats: Dict,
        revenue_stats: Dict
    ) -> str:
        summary = {
            "date": summary_date,
            "patients": patient_stats,
            "appointments": appointment_stats,
            "consultations": consultation_stats,
            "pharmacy": pharmacy_stats,
            "revenue": revenue_stats,
            "generated_at": datetime.utcnow()
        }

        result = await self.collection.update_one(
            {"date": summary_date},
            {"$set": summary},
            upsert=True
        )

        return str(result.upserted_id) if result.upserted_id else "updated"

    async def get_summary(self, summary_date: date) -> Optional[Dict]:
        """Get summary for specific date"""
        doc = await self.collection.find_one({"date": summary_date})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def get_summaries_range(
        self,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Get summaries for date range"""
        cursor = self.collection.find({
            "date": {
                "$gte": start_date,
                "$lte": end_date
            }
        }).sort("date", -1)

        summaries = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            summaries.append(doc)

        return summaries