import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.payment import PaymentFeatureInputs

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["app"] == "RecoverAI"
    assert payload["database"]["status"] == "connected"

def test_get_payments_paginated():
    response = client.get("/api/payments?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 10
    assert data["total"] >= 1000
    assert data["page"] == 1
    assert data["page_size"] == 10

def test_get_payments_filtered():
    response = client.get("/api/payments?payment_method=upi&status=FAILED&min_amount=500")
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["payment_method"] == "upi"
        assert item["status"] == "FAILED"
        assert item["amount"] >= 500.0

def test_get_payment_detail():
    # Fetch first payment ID from list
    list_res = client.get("/api/payments?page=1&page_size=1")
    assert list_res.status_code == 200
    first_payment = list_res.json()["items"][0]
    payment_id = first_payment["payment_id"]

    # Fetch detail
    detail_res = client.get(f"/api/payments/{payment_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["payment_id"] == payment_id
    assert detail_data["amount"] == first_payment["amount"]

def test_get_payment_not_found():
    response = client.get("/api/payments/pay_nonexistent99999")
    assert response.status_code == 404
    assert "Payment not found" in response.json()["detail"]

def test_get_customers_paginated():
    response = client.get("/api/customers?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 5
    assert data["total"] >= 300

def test_get_customer_detail():
    list_res = client.get("/api/customers?page=1&page_size=1")
    assert list_res.status_code == 200
    first_cust = list_res.json()["items"][0]
    customer_id = first_cust["customer_id"]

    detail_res = client.get(f"/api/customers/{customer_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["customer_id"] == customer_id

def test_get_customer_not_found():
    response = client.get("/api/customers/cust_nonexistent999")
    assert response.status_code == 404
    assert "Customer not found" in response.json()["detail"]

def test_metrics_overview():
    response = client.get("/api/metrics/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["total_failed_payments"] >= 1000
    assert data["total_revenue_at_risk"] > 0
    assert data["average_payment_amount"] > 0
    assert "network_failure" in data["payment_count_by_failure_reason"]
    assert "upi" in data["payment_count_by_payment_method"]

def test_metrics_failure_reasons():
    response = client.get("/api/metrics/failure-reasons")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    reasons = [item["failure_reason"] for item in data]
    assert "temporary_bank_error" in reasons

def test_metrics_payment_methods():
    response = client.get("/api/metrics/payment-methods")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    methods = [item["payment_method"] for item in data]
    assert "upi" in methods

def test_ground_truth_leakage_prevention_in_features():
    fields = set(PaymentFeatureInputs.model_fields.keys())
    assert "recovered" not in fields
    assert "amount_recovered" not in fields
    assert "true_recovery_probability" not in fields
