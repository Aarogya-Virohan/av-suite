"""
Base interfaces for third-party integrations (Payment Gateways, Storage, Notifications).
Keeps external service logic decoupled from core business services.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BasePaymentGateway(ABC):
    """Abstract interface for payment gateway integrations (e.g. Razorpay, Stripe)."""

    @abstractmethod
    async def create_payment_intent(self, amount: int, currency: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create a payment intent or order."""
        pass

    @abstractmethod
    async def verify_payment_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """Verify webhooks or payment response signatures."""
        pass


class BaseStorageService(ABC):
    """Abstract interface for file storage integrations (e.g. Supabase Storage, AWS S3)."""

    @abstractmethod
    async def upload_file(self, file_bytes: bytes, file_name: str, content_type: str) -> str:
        """Upload file and return public or signed URL."""
        pass

    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage."""
        pass
