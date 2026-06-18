# Booking Manager API

A small FastAPI application for tracking bookings, package selections, payment status, invoices, reminders, and gig expenses.

## Features

- Add bookings for small, medium, and large packages
- Track whether a client paid a deposit or paid in full
- Prevent more than 3 bookings on the same date
- Create invoices for bookings
- Trigger reminders for upcoming gigs
- Track income, expenses, outstanding balances, and net income
- Record planning and post-gig expenses for items, food, and labour

## Getting Started

1. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:

   ```bash
   python src/app.py
   ```

3. Open your browser and go to:
   - App: http://localhost:8000
   - API documentation: http://localhost:8000/docs

## API Endpoints

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/packages` | Get available package prices |
| GET | `/bookings` | List all bookings |
| POST | `/bookings` | Create a booking |
| POST | `/bookings/{booking_id}/invoice` | Create or fetch a booking invoice |
| POST | `/bookings/{booking_id}/expenses` | Record a booking expense |
| GET | `/reminders/upcoming` | List upcoming gigs that need reminders |
| POST | `/bookings/{booking_id}/reminders/trigger` | Trigger a reminder for a booking |
| GET | `/finance/summary` | View income, expenses, balances, and net income |

All data is stored in memory, so it resets when the application restarts.
