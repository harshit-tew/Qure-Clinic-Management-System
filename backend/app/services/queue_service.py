from datetime import datetime, date
from typing import List, Optional, Dict
from redis.asyncio import Redis
import json


class QueueService:


    def __init__(self, redis: Redis):
        self.redis = redis

    def _get_queue_key(self, queue_date: date) -> str:
        """Get Redis key for queue sorted set"""
        return f"queue:{queue_date.isoformat()}"

    def _get_token_key(self, queue_date: date, token_number: int) -> str:
        """Get Redis key for token data hash"""
        return f"queue:token:{queue_date.isoformat()}:{token_number}"

    def _get_counter_key(self, queue_date: date) -> str:
        """Get Redis key for token counter"""
        return f"queue:counter:{queue_date.isoformat()}"

    def _get_current_key(self, queue_date: date) -> str:
        """Get Redis key for current serving token"""
        return f"queue:current:{queue_date.isoformat()}"

    async def _get_next_token_number(self, queue_date: date) -> int:
        """Get next token number for the day (atomic increment)"""
        counter_key = self._get_counter_key(queue_date)
        token_number = await self.redis.incr(counter_key)

        await self.redis.expire(counter_key, 86400)

        return token_number

    async def check_in(
        self,
        queue_date: date,
        patient_id: int,
        patient_name: str,
        appointment_id: Optional[int] = None,
        is_walk_in: bool = False,
        chief_complaint: Optional[str] = None
    ) -> Dict:
        """
        Check in a patient (appointment or walk-in)

        Returns token data
        """
        token_number = await self._get_next_token_number(queue_date)
        checkin_time = datetime.utcnow()
        checkin_timestamp = checkin_time.timestamp()

        token_data = {
            "token_number": token_number,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "appointment_id": appointment_id or "",
            "status": "WAITING",
            "checkin_time": checkin_time.isoformat(),
            "called_time": "",
            "completed_time": "",
            "is_walk_in": str(is_walk_in),
            "chief_complaint": chief_complaint or ""
        }

        token_key = self._get_token_key(queue_date, token_number)
        await self.redis.hset(token_key, mapping=token_data)
        await self.redis.expire(token_key, 86400)

        queue_key = self._get_queue_key(queue_date)
        await self.redis.zadd(queue_key, {str(token_number): checkin_timestamp})
        await self.redis.expire(queue_key, 86400)

        return token_data

    async def get_today_queue(self, queue_date: date) -> List[Dict]:
        """
        Get all tokens for today in order

        Returns list of token data sorted by checkin time
        """
        queue_key = self._get_queue_key(queue_date)

        token_numbers = await self.redis.zrange(queue_key, 0, -1)

        if not token_numbers:
            return []

        tokens = []
        for token_num_str in token_numbers:
            token_key = self._get_token_key(queue_date, int(token_num_str))
            token_data = await self.redis.hgetall(token_key)

            if token_data:
                tokens.append({
                    "token_number": int(token_data["token_number"]),
                    "patient_id": int(token_data["patient_id"]),
                    "patient_name": token_data["patient_name"],
                    "appointment_id": int(token_data["appointment_id"]) if token_data.get("appointment_id") else None,
                    "status": token_data["status"],
                    "checkin_time": token_data["checkin_time"],
                    "called_time": token_data.get("called_time") or None,
                    "completed_time": token_data.get("completed_time") or None,
                    "is_walk_in": token_data.get("is_walk_in") == "True",
                    "chief_complaint": token_data.get("chief_complaint") or None
                })

        return tokens

    async def update_status(
        self,
        queue_date: date,
        token_number: int,
        new_status: str
    ) -> Optional[Dict]:
        """
        Update token status

        Valid statuses: WAITING, WITH_DOCTOR, COMPLETED, SKIPPED, NO_SHOW
        """
        token_key = self._get_token_key(queue_date, token_number)

        exists = await self.redis.exists(token_key)
        if not exists:
            return None

        await self.redis.hset(token_key, "status", new_status)

        now = datetime.utcnow().isoformat()
        if new_status == "WITH_DOCTOR":
            await self.redis.hset(token_key, "called_time", now)
            current_key = self._get_current_key(queue_date)
            await self.redis.set(current_key, token_number, ex=86400)

        elif new_status in ["COMPLETED", "NO_SHOW"]:
            await self.redis.hset(token_key, "completed_time", now)
            current_key = self._get_current_key(queue_date)
            current = await self.redis.get(current_key)
            if current and int(current) == token_number:
                await self.redis.delete(current_key)

        token_data = await self.redis.hgetall(token_key)
        return {
            "token_number": int(token_data["token_number"]),
            "patient_id": int(token_data["patient_id"]),
            "patient_name": token_data["patient_name"],
            "appointment_id": int(token_data["appointment_id"]) if token_data.get("appointment_id") else None,
            "status": token_data["status"],
            "checkin_time": token_data["checkin_time"],
            "called_time": token_data.get("called_time") or None,
            "completed_time": token_data.get("completed_time") or None,
            "is_walk_in": token_data.get("is_walk_in") == "True"
        }

    async def get_current_serving(self, queue_date: date) -> Optional[int]:
        """Get currently serving token number"""
        current_key = self._get_current_key(queue_date)
        current = await self.redis.get(current_key)
        return int(current) if current else None

    async def call_next_patient(self, queue_date: date) -> Optional[Dict]:
        """
        Call next patient from WAITING queue

        Finds first WAITING token and marks as WITH_DOCTOR
        Returns token data or None if no one waiting
        """
        tokens = await self.get_today_queue(queue_date)

        for token in tokens:
            if token["status"] == "WAITING":
                return await self.update_status(
                    queue_date,
                    token["token_number"],
                    "WITH_DOCTOR"
                )

        return None

    async def skip_patient(self, queue_date: date, token_number: int) -> Optional[Dict]:

        return await self.update_status(queue_date, token_number, "SKIPPED")

    async def recall_patient(self, queue_date: date, token_number: int) -> Optional[Dict]:

        return await self.update_status(queue_date, token_number, "WAITING")

    async def get_queue_summary(self, queue_date: date) -> Dict:

        tokens = await self.get_today_queue(queue_date)

        summary = {
            "date": queue_date.isoformat(),
            "total_tokens": len(tokens),
            "checked_in": 0,
            "waiting": 0,
            "with_doctor": 0,
            "completed": 0,
            "skipped": 0,
            "no_show": 0,
            "current_token": await self.get_current_serving(queue_date),
            "tokens": tokens
        }

        for token in tokens:
            status = token["status"]
            if status == "WAITING":
                summary["waiting"] += 1
            elif status == "WITH_DOCTOR":
                summary["with_doctor"] += 1
            elif status == "COMPLETED":
                summary["completed"] += 1
            elif status == "SKIPPED":
                summary["skipped"] += 1
            elif status == "NO_SHOW":
                summary["no_show"] += 1

        summary["checked_in"] = summary["waiting"] + summary["with_doctor"]

        return summary