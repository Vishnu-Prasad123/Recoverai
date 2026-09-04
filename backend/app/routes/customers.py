from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.customer_service import CustomerService
from app.schemas.customer import CustomerRead, PaginatedCustomerResponse

router = APIRouter(prefix="/api/customers", tags=["Customers API"])

@router.get("", response_model=PaginatedCustomerResponse)
def get_customers(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Retrieves paginated list of customer profiles.
    """
    items, total, total_pages = CustomerService.get_customers(
        db=db,
        page=page,
        page_size=page_size
    )

    return PaginatedCustomerResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer_detail(customer_id: str, db: Session = Depends(get_db)):
    """
    Retrieves a single customer profile by customer_id.
    Returns HTTP 404 if customer is not found.
    """
    customer = CustomerService.get_customer_by_id(db, customer_id=customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer not found with ID '{customer_id}'"
        )
    return customer
