from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class CustomerBase(BaseModel):
    customer_id: str
    name: str
    email: str
    phone: Optional[str] = None
    lifetime_value: float = 0.0
    total_payments_count: int = 0
    successful_payments_count: int = 0
    success_rate: float = 1.0

class CustomerRead(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PaginatedCustomerResponse(BaseModel):
    items: List[CustomerRead]
    total: int
    page: int
    page_size: int
    total_pages: int
