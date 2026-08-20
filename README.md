# Kapture Finance – AI Voice Collection Agent

An AI-powered voice collection agent built for Kapture Finance to automate customer payment collection calls.

The agent verifies the customer's identity, retrieves account information from MySQL, discusses overdue payments, captures payment commitments, and records the final call disposition.

## Features

- AI-powered voice conversations using Vapi
- Customer identity verification
- MySQL-based customer and account retrieval
- Overdue payment information retrieval
- Promise-to-Pay (PTP) capture
- Payment commitment date and amount recording
- Collection call disposition tracking
- Persistent call records in MySQL
- FastAPI webhook backend
- Secure environment variable configuration

## Technology Stack

### Backend

- Python
- FastAPI
- Uvicorn

### AI Voice

- Vapi

### Database

- MySQL

### Networking

- Cloudflare Tunnel

### Development

- Git
- GitHub

## Vapi Tools

The voice agent uses custom tools connected to the FastAPI webhook.

### 1. verify_customer

Verifies the customer's identity using the customer name and verification code.

### 2. get_account_details

Retrieves authenticated customer account information including:

- Loan type
- Overdue amount
- Days past due

### 3. log_promise_to_pay

Records a customer's payment commitment including:

- Payment amount
- Promise-to-pay date
- PTP reference

### 4. mark_disposition

Records the final outcome of the collection call.

Supported dispositions include:

- `PTP_AGREED`
- `ALREADY_PAID`
- `DISPUTED`
- `HARDSHIP_ESCALATED`
- `WRONG_PERSON`
- `DO_NOT_CALL`
- `NO_RESPONSE`
- `AUTH_FAILED`

## Database Design

The project uses a MySQL database named:

`kapture_finance`

### customers

Stores customer and loan information.

Important fields:

- `id`
- `account_id`
- `customer_name`
- `verification_code`
- `loan_type`
- `overdue_amount`
- `days_past_due`
- `phone`
- `created_at`

### collection_calls

Stores persistent collection call information.

Important fields:

- `id`
- `call_id`
- `customer_id`
- `verification_status`
- `disposition`
- `notes`
- `ptp_amount`
- `ptp_date`
- `created_at`
- `updated_at`

## Call Flow

Customer
→ Vapi AI Voice Agent
→ FastAPI Webhook
→ Customer Verification
→ Account Details
→ Payment Discussion
→ Promise to Pay / Final Disposition
→ MySQL

## Data Flow

1. Vapi initiates the voice conversation.
2. The customer provides identity information.
3. FastAPI verifies the customer using MySQL.
4. Account and overdue payment details are retrieved.
5. The agent discusses the outstanding payment.
6. The customer's payment intent is recorded.
7. The final call disposition is stored.
8. The complete collection outcome is persisted in MySQL.

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/Karthikhugar17/kapture-collection-voicebot.git
cd kapture-collection-voicebot
```

### 2. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 3. Configure environment variables

Create a `.env` file inside the `backend` directory and add the required API keys and database configuration.

Sensitive credentials should never be committed to GitHub.

### 4. Start the FastAPI server

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 5. Start the Cloudflare tunnel

```bash
cloudflared.exe tunnel --url http://localhost:8000
```

Configure the generated HTTPS URL as the webhook URL in the Vapi tools.

## Tested Outcomes

The system has been successfully tested with real Vapi voice calls for:

- `PTP_AGREED`
- `ALREADY_PAID`
- `HARDSHIP_ESCALATED`
- `NO_RESPONSE`

The corresponding call outcomes are persisted in the MySQL `collection_calls` table.

## Example

Demo customer:

- Customer: Rahul Sharma
- Loan Type: Personal Loan
- Overdue Amount: ₹8,499
- Days Past Due: 12

Example Promise-to-Pay:

- Disposition: `PTP_AGREED`
- Amount: ₹8,499
- Promise Date: 2026-08-21

## Security

Sensitive information such as API keys, database credentials, and webhook secrets are stored in environment variables.

The `.env` file and Python cache files are excluded from Git using `.gitignore`.

## Project Outcome

The project demonstrates an end-to-end AI voice collection workflow where Vapi handles the voice interaction, FastAPI handles business logic, and MySQL provides persistent storage for customer and collection data.

## Author

Karthik Hugar
