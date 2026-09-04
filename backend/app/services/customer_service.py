import math
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from app.models.customer import Customer

class CustomerService:
    @staticmethod
    def get_customers(
        db: Session,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Customer], int, int]:
        """
        Retrieves paginated customer records.
        Returns (customers_list, total_count, total_pages).
        """
        query = db.query(Customer)
        total_count = query.count()
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

        offset = (page - 1) * page_size
        customers = query.order_by(Customer.created_at.desc()).offset(offset).limit(page_size).all()

        return customers, total_count, total_pages

    @staticmethod
    def get_customer_by_id(db: Session, customer_id: str) -> Optional[Customer]:
        """Fetches a single customer profile by customer_id."""
        return db.query(Customer).filter(Customer.customer_id == customer_id).first()
