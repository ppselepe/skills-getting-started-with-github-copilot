from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from src.app import PACKAGE_PRICES, app, bookings

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_bookings():
    bookings.clear()
    yield
    bookings.clear()


def create_booking(event_date: date, payment_type: str = "deposit", amount_paid: float = 1000.0):
    return client.post(
        "/bookings",
        json={
            "client_name": "Alice",
            "client_email": "alice@example.com",
            "event_date": event_date.isoformat(),
            "package_size": "small",
            "payment_type": payment_type,
            "amount_paid": amount_paid,
        },
    )


def test_create_booking_tracks_package_and_payment_status():
    response = create_booking(date.today() + timedelta(days=10))

    assert response.status_code == 201
    data = response.json()
    assert data["package_size"] == "small"
    assert data["payment_type"] == "deposit"
    assert data["amount_paid"] == 1000.0
    assert data["balance_due"] == PACKAGE_PRICES["small"] - 1000.0


def test_prevents_more_than_three_bookings_on_same_date():
    booking_date = date.today() + timedelta(days=20)

    for index in range(3):
        response = client.post(
            "/bookings",
            json={
                "client_name": f"Client {index}",
                "client_email": f"client{index}@example.com",
                "event_date": booking_date.isoformat(),
                "package_size": "medium",
                "payment_type": "deposit",
                "amount_paid": 1500.0,
            },
        )
        assert response.status_code == 201

    response = client.post(
        "/bookings",
        json={
            "client_name": "Overflow Client",
            "client_email": "overflow@example.com",
            "event_date": booking_date.isoformat(),
            "package_size": "large",
            "payment_type": "deposit",
            "amount_paid": 2000.0,
        },
    )

    assert response.status_code == 409
    assert "Only 3 bookings" in response.json()["detail"]


def test_invoice_reminders_and_finance_summary_include_expenses():
    booking_date = date.today() + timedelta(days=4)
    booking_response = client.post(
        "/bookings",
        json={
            "client_name": "Booked Client",
            "client_email": "booked@example.com",
            "event_date": booking_date.isoformat(),
            "package_size": "medium",
            "payment_type": "paid_in_full",
            "amount_paid": PACKAGE_PRICES["medium"],
        },
    )
    booking_id = booking_response.json()["id"]

    invoice_response = client.post(f"/bookings/{booking_id}/invoice")
    reminder_response = client.post(f"/bookings/{booking_id}/reminders/trigger")
    client.post(
        f"/bookings/{booking_id}/expenses",
        json={"category": "items", "description": "Decor", "amount": 600.0},
    )
    client.post(
        f"/bookings/{booking_id}/expenses",
        json={"category": "labour", "description": "Setup crew", "amount": 300.0},
    )

    reminders_response = client.get("/reminders/upcoming?days=7")
    finance_response = client.get("/finance/summary")

    assert invoice_response.status_code == 200
    assert invoice_response.json()["invoice_number"].startswith("INV-")
    assert reminder_response.status_code == 200
    assert reminder_response.json()["days_until_event"] == 4
    assert reminders_response.status_code == 200
    assert reminders_response.json()[0]["booking_id"] == booking_id

    finance = finance_response.json()
    assert finance["total_income"] == PACKAGE_PRICES["medium"]
    assert finance["total_expenses"] == 900.0
    assert finance["net_income"] == PACKAGE_PRICES["medium"] - 900.0
    assert finance["expenses_by_category"]["items"] == 600.0
    assert finance["expenses_by_category"]["labour"] == 300.0
