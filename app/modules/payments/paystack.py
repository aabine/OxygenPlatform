from typing import Optional, Dict, Any
import httpx
from fastapi import HTTPException
from app.core.config import settings

class PaystackService:
    BASE_URL = "https://api.paystack.co"
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }

    async def initialize_payment(
        self,
        amount: float,
        email: str,
        reference: Optional[str] = None,
        callback_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Initialize a payment transaction with Paystack"""
        url = f"{self.BASE_URL}/transaction/initialize"
        
        # Amount should be in kobo (multiply by 100)
        payload = {
            "amount": int(amount * 100),
            "email": email,
            "currency": "NGN"
        }
        
        if reference:
            payload["reference"] = reference
        if callback_url:
            payload["callback_url"] = callback_url
        if metadata:
            payload["metadata"] = metadata

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to initialize payment"
                )
                
            data = response.json()
            if not data["status"]:
                raise HTTPException(
                    status_code=400,
                    detail=data.get("message", "Payment initialization failed")
                )
                
            return data["data"]

    async def verify_payment(self, reference: str) -> Dict[str, Any]:
        """Verify a payment transaction"""
        url = f"{self.BASE_URL}/transaction/verify/{reference}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to verify payment"
                )
                
            data = response.json()
            if not data["status"]:
                raise HTTPException(
                    status_code=400,
                    detail=data.get("message", "Payment verification failed")
                )
                
            return data["data"]

    def verify_webhook_signature(self, signature: str, payload: bytes) -> bool:
        """Verify that the webhook is from Paystack"""
        import hmac
        import hashlib
        
        secret = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
        hash_obj = hmac.new(secret, payload, hashlib.sha512)
        calculated_hash = hash_obj.hexdigest()
        
        return hmac.compare_digest(calculated_hash, signature)

    async def initiate_refund(
        self,
        transaction_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initiate a refund for a transaction"""
        url = f"{self.BASE_URL}/refund"
        
        payload = {"transaction": transaction_id}
        
        # Amount should be in kobo if provided
        if amount:
            payload["amount"] = int(amount * 100)
        if reason:
            payload["merchant_note"] = reason

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to initiate refund"
                )
                
            data = response.json()
            if not data["status"]:
                raise HTTPException(
                    status_code=400,
                    detail=data.get("message", "Refund initiation failed")
                )
                
            return data["data"]

    async def get_transaction_timeline(self, transaction_id: str) -> Dict[str, Any]:
        """Get the timeline of a transaction"""
        url = f"{self.BASE_URL}/transaction/timeline/{transaction_id}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to get transaction timeline"
                )
                
            data = response.json()
            return data["data"]

    async def get_transaction_totals(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get transaction totals within a date range"""
        url = f"{self.BASE_URL}/transaction/totals"
        params = {}
        
        if start_date:
            params["from"] = start_date
        if end_date:
            params["to"] = end_date

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=self.headers)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to get transaction totals"
                )
                
            data = response.json()
            return data["data"]
