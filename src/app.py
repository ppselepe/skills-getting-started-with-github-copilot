"""
Booking management API.

A small FastAPI application for tracking bookings, invoices, reminders,
incoming payments, and gig-related expenses.
"""

from datetime import UTC, date, datetime
import os
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

PACKAGE_PRICES = {
    "small": 2500.0,
    "medium": 5000.0,
    "large": 9000.0,
}
MAX_BOOKINGS_PER_DAY = 3

app = FastAPI(
    title="Booking Manager API",
    description=(
        "API for tracking bookings, invoices, reminders, payments, "
        "and event expenses."
    ),
)

current_dir = Path(__file__).parent
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(current_dir, "static")),
    name="static",
)

bookings: list[dict] = []


class BookingCreate(BaseModel):
    client_name: str = Field(min_length=1)
    client_email: str = Field(min_length=3)
    event_date: date
    package_size: Literal["small", "medium", "large"]
    payment_type: Literal["deposit", "paid_in_full"]
    amount_paid: float = Field(gt=0)


class ExpenseCreate(BaseModel):
    category: Literal["items", "food", "labour"]
    description: str = Field(min_length=1)
    amount: float = Field(gt=0)


def get_booking_or_404(booking_id: str) -> dict:
    for booking in bookings:
        if booking["id"] == booking_id:
            return booking
    raise HTTPException(status_code=404, detail="Booking not found")


def calculate_balance(booking: dict) -> float:
    return round(booking["package_price"] - booking["amount_paid"], 2)


def serialize_booking(booking: dict) -> dict:
    expenses_total = round(sum(expense["amount"] for expense in booking["expenses"]), 2)
    return {
        "id": booking["id"],
        "client_name": booking["client_name"],
        "client_email": booking["client_email"],
        "event_date": booking["event_date"].isoformat(),
        "package_size": booking["package_size"],
        "package_price": booking["package_price"],
        "payment_type": booking["payment_type"],
        "amount_paid": booking["amount_paid"],
        "balance_due": calculate_balance(booking),
        "invoice_number": booking["invoice_number"],
        "expense_total": expenses_total,
        "expenses": booking["expenses"],
        "reminders_sent": booking["reminders"],
    }


def validate_payment_details(payload: BookingCreate, package_price: float) -> None:
    if payload.amount_paid > package_price:
        raise HTTPException(
            status_code=400,
            detail="Amount paid cannot be more than the package price",
        )

    if payload.payment_type == "deposit" and payload.amount_paid >= package_price:
        raise HTTPException(
            status_code=400,
            detail="A deposit must be less than the full package price",
        )

    if payload.payment_type == "paid_in_full" and payload.amount_paid < package_price:
        raise HTTPException(
            status_code=400,
            detail="A full payment must cover the full package price",
        )


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/packages")
def get_packages():
    return PACKAGE_PRICES


@app.get("/bookings")
def get_bookings():
    return [serialize_booking(booking) for booking in bookings]


@app.post("/bookings", status_code=status.HTTP_201_CREATED)
def create_booking(payload: BookingCreate):
    daily_bookings = sum(1 for booking in bookings if booking["event_date"] == payload.event_date)
    if daily_bookings >= MAX_BOOKINGS_PER_DAY:
        raise HTTPException(
            status_code=409,
            detail=f"Only {MAX_BOOKINGS_PER_DAY} bookings can be taken on the same date",
        )

    package_price = PACKAGE_PRICES[payload.package_size]
    validate_payment_details(payload, package_price)

    booking = {
        "id": str(uuid4()),
        "client_name": payload.client_name,
        "client_email": payload.client_email,
        "event_date": payload.event_date,
        "package_size": payload.package_size,
        "package_price": package_price,
        "payment_type": payload.payment_type,
        "amount_paid": round(payload.amount_paid, 2),
        "invoice_number": None,
        "expenses": [],
        "reminders": [],
    }
    bookings.append(booking)
    return serialize_booking(booking)


@app.post("/bookings/{booking_id}/invoice")
def create_invoice(booking_id: str):
    booking = get_booking_or_404(booking_id)
    if booking["invoice_number"] is None:
        booking["invoice_number"] = f"INV-{booking['id'][:8].upper()}"

    return {
        "invoice_number": booking["invoice_number"],
        "client_name": booking["client_name"],
        "client_email": booking["client_email"],
        "event_date": booking["event_date"].isoformat(),
        "package_size": booking["package_size"],
        "total_due": booking["package_price"],
        "amount_paid": booking["amount_paid"],
        "balance_due": calculate_balance(booking),
        "payment_status": booking["payment_type"],
    }


@app.post("/bookings/{booking_id}/expenses")
def add_expense(booking_id: str, payload: ExpenseCreate):
    booking = get_booking_or_404(booking_id)
    expense = {
        "id": str(uuid4()),
        "category": payload.category,
        "description": payload.description,
        "amount": round(payload.amount, 2),
    }
    booking["expenses"].append(expense)
    return {
        "message": "Expense recorded",
        "booking_id": booking_id,
        "expense": expense,
    }


@app.get("/reminders/upcoming")
def get_upcoming_reminders(days: int = 7):
    upcoming = []
    for booking in bookings:
        days_until_event = (booking["event_date"] - date.today()).days
        if 0 <= days_until_event <= days:
            upcoming.append(
                {
                    "booking_id": booking["id"],
                    "client_name": booking["client_name"],
                    "event_date": booking["event_date"].isoformat(),
                    "days_until_event": days_until_event,
                    "balance_due": calculate_balance(booking),
                }
            )
    return upcoming


@app.post("/bookings/{booking_id}/reminders/trigger")
def trigger_reminder(booking_id: str):
    booking = get_booking_or_404(booking_id)
    days_until_event = (booking["event_date"] - date.today()).days
    reminder = {
        "sent_at": datetime.now(UTC).isoformat(),
        "days_until_event": days_until_event,
    }
    booking["reminders"].append(reminder)
    return {
        "message": (
            f"Reminder triggered for {booking['client_name']} "
            f"({booking['event_date'].isoformat()})"
        ),
        "days_until_event": days_until_event,
        "balance_due": calculate_balance(booking),
    }


@app.get("/finance/summary")
def get_finance_summary():
    total_income = round(sum(booking["amount_paid"] for booking in bookings), 2)
    total_expenses = round(
        sum(expense["amount"] for booking in bookings for expense in booking["expenses"]),
        2,
    )
    expenses_by_category = {
        "items": round(
            sum(
                expense["amount"]
                for booking in bookings
                for expense in booking["expenses"]
                if expense["category"] == "items"
            ),
            2,
        ),
        "food": round(
            sum(
                expense["amount"]
                for booking in bookings
                for expense in booking["expenses"]
                if expense["category"] == "food"
            ),
            2,
        ),
        "labour": round(
            sum(
                expense["amount"]
                for booking in bookings
                for expense in booking["expenses"]
                if expense["category"] == "labour"
            ),
            2,
        ),
    }
    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_income": round(total_income - total_expenses, 2),
        "outstanding_balances": round(sum(calculate_balance(booking) for booking in bookings), 2),
        "expenses_by_category": expenses_by_category,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
