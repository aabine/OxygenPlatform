from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from app.modules.payments.models import Transaction, PaymentStatus
from app.modules.orders.models import Order

class PaymentAnalytics:
    def __init__(self, db: Session):
        self.db = db

    async def get_payment_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        vendor_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get payment summary statistics"""
        query = select(
            func.count(Transaction.id).label('total_transactions'),
            func.sum(Transaction.total_amount).label('total_amount'),
            func.sum(Transaction.platform_fee).label('total_fees'),
            func.avg(Transaction.total_amount).label('average_transaction')
        ).where(Transaction.status == PaymentStatus.SUCCESS)

        if start_date:
            query = query.where(Transaction.created_at >= start_date)
        if end_date:
            query = query.where(Transaction.created_at <= end_date)
        if vendor_id:
            query = query.where(Transaction.vendor_id == vendor_id)

        result = self.db.execute(query).first()

        return {
            "total_transactions": result.total_transactions or 0,
            "total_amount": float(result.total_amount or 0),
            "total_fees": float(result.total_fees or 0),
            "average_transaction": float(result.average_transaction or 0)
        }

    async def get_daily_transactions(
        self,
        days: int = 30,
        vendor_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get daily transaction counts and amounts"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        query = select(
            func.date(Transaction.created_at).label('date'),
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.total_amount).label('amount')
        ).where(
            and_(
                Transaction.created_at >= start_date,
                Transaction.created_at <= end_date,
                Transaction.status == PaymentStatus.SUCCESS
            )
        ).group_by(func.date(Transaction.created_at))

        if vendor_id:
            query = query.where(Transaction.vendor_id == vendor_id)

        results = self.db.execute(query).all()

        return [
            {
                "date": result.date.isoformat(),
                "count": result.count,
                "amount": float(result.amount or 0)
            }
            for result in results
        ]

    async def get_payment_status_distribution(
        self,
        vendor_id: Optional[int] = None
    ) -> Dict[str, int]:
        """Get distribution of payment statuses"""
        query = select(
            Transaction.status,
            func.count(Transaction.id).label('count')
        ).group_by(Transaction.status)

        if vendor_id:
            query = query.where(Transaction.vendor_id == vendor_id)

        results = self.db.execute(query).all()

        return {str(result.status): result.count for result in results}

    async def get_vendor_performance(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Get top performing vendors by transaction volume"""
        query = select(
            Transaction.vendor_id,
            func.count(Transaction.id).label('transaction_count'),
            func.sum(Transaction.total_amount).label('total_amount'),
            func.avg(Transaction.total_amount).label('average_amount')
        ).where(Transaction.status == PaymentStatus.SUCCESS
        ).group_by(Transaction.vendor_id
        ).order_by(func.sum(Transaction.total_amount).desc()
        ).limit(top_n)

        results = self.db.execute(query).all()

        return [
            {
                "vendor_id": result.vendor_id,
                "transaction_count": result.transaction_count,
                "total_amount": float(result.total_amount or 0),
                "average_amount": float(result.average_amount or 0)
            }
            for result in results
        ]

    async def get_payment_method_stats(
        self,
        vendor_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get statistics by payment method"""
        query = select(
            Transaction.payment_method,
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.total_amount).label('total_amount')
        ).where(
            Transaction.status == PaymentStatus.SUCCESS
        ).group_by(Transaction.payment_method)

        if vendor_id:
            query = query.where(Transaction.vendor_id == vendor_id)

        results = self.db.execute(query).all()

        return {
            str(result.payment_method): {
                "count": result.count,
                "total_amount": float(result.total_amount or 0)
            }
            for result in results
        }
