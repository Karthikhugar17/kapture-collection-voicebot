# Kapture Finance – AI-Powered Voice Collection & Recovery Platform

An end-to-end AI-powered collection and recovery platform designed to automate customer payment collection workflows.

The system combines an AI voice agent, FastAPI backend, MySQL database, follow-up management, customer risk classification, and a Streamlit analytics dashboard.

The voice agent can verify customers, retrieve loan information, discuss overdue payments, capture Promise-to-Pay commitments, record call outcomes, and persist the complete collection workflow in MySQL.

---

# Architecture

```text
                         ┌──────────────────────┐
                         │    Customer Call     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Vapi AI Voice      │
                         │       Agent          │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   FastAPI Backend    │
                         │                      │
                         │  • Verification      │
                         │  • Account Lookup    │
                         │  • PTP Management    │
                         │  • Dispositions      │
                         │  • Follow-ups        │
                         │  • Risk Analytics    │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │        MySQL         │
                         │                      │
                         │ • Customers          │
                         │ • Collection Calls   │
                         │ • PTP Follow-ups     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Streamlit Dashboard  │
                         │                      │
                         │ • Call Analytics     │
                         │ • Follow-ups         │
                         │ • Customer Portfolio │
                         │ • Risk Analytics     │
                         └──────────────────────┘
```

---

# Features

## AI Voice Collection Agent

- AI-powered voice conversations using Vapi
- Customer identity verification
- Customer account retrieval
- Overdue payment information retrieval
- Payment discussion workflow
- Promise-to-Pay capture
- Payment commitment amount and date recording
- Final collection disposition tracking

## Collection Management

- Persistent collection call records
- Call history retrieval
- Individual call details
- Collection disposition tracking
- Promise-to-Pay tracking
- Follow-up scheduling
- Follow-up status management
- Follow-up attempt tracking
- Due follow-up detection

## Customer Portfolio Management

- Multi-customer support
- Customer account portfolio
- Overdue amount tracking
- Days Past Due tracking
- Customer risk classification

Risk levels are automatically calculated based on Days Past Due:

```text
25+ Days Past Due → HIGH
15–24 Days Past Due → MEDIUM
0–14 Days Past Due → LOW
```

## Analytics Dashboard

The Streamlit dashboard provides:

- Total collection calls
- PTP agreed count
- Already paid count
- Hardship cases
- No response count
- Total promised payment amount
- Collection disposition chart
- Collection call history
- Individual call details
- Follow-up management
- Due follow-up tracking
- Pending follow-up actions
- Customer portfolio metrics
- Total overdue amount
- High-risk customer count
- Customer risk distribution chart

---

# Technology Stack

## Backend

- Python
- FastAPI
- Uvicorn

## AI Voice

- Vapi

## Database

- MySQL

## Dashboard

- Streamlit
- Pandas

## Networking

- Cloudflare Tunnel

## Development

- Git
- GitHub

---

# Vapi Tools

The AI voice agent uses custom tools connected to the FastAPI backend.

## 1. verify_customer

Verifies the customer's identity using customer information and a verification code.

---

## 2. get_account_details

Retrieves authenticated customer account information including:

- Loan type
- Overdue amount
- Days Past Due

---

## 3. log_promise_to_pay

Records a customer's payment commitment including:

- Payment amount
- Promise-to-Pay date
- PTP reference
- Follow-up information

---

## 4. mark_disposition

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

---

# REST APIs

## Collection Calls

```text
GET /calls
```

Retrieves collection call history.

```text
GET /calls/{call_id}
```

Retrieves detailed information for a specific collection call.

---

## Analytics

```text
GET /analytics
```

Returns collection analytics including:

- Total calls
- PTP agreed
- Already paid
- Hardship escalated
- No response
- Total PTP amount

---

## Follow-ups

```text
GET /followups
```

Retrieves pending follow-ups.

```text
GET /followups/due
```

Retrieves follow-ups that are currently due.

```text
PUT /followups/{call_id}
```

Updates follow-up status and optionally increments the attempt count.

---

## Customers

```text
GET /customers
```

Returns the customer portfolio including:

- Customer information
- Loan type
- Overdue amount
- Days Past Due
- Risk level

Customers are automatically ordered by Days Past Due.

---

# Database Design

The project uses a MySQL database named:

```text
kapture_finance
```

## customers

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

---

## collection_calls

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
- `follow_up_status`
- `follow_up_date`
- `attempt_count`
- `created_at`
- `updated_at`

---

# Collection Workflow

```text
Customer Call
     ↓
Vapi AI Voice Agent
     ↓
Customer Verification
     ↓
Account Information Retrieval
     ↓
Overdue Payment Discussion
     ↓
Payment Decision
     │
     ├── Promise to Pay
     │       ↓
     │   Follow-up Created
     │
     ├── Already Paid
     │
     ├── Hardship Escalation
     │
     └── Other Disposition
     ↓
Collection Outcome Stored
     ↓
MySQL
     ↓
Analytics Dashboard
```

---

# Local Setup

## 1. Clone the Repository

```bash
git clone https://github.com/Karthikhugar17/kapture-collection-voicebot.git
cd kapture-collection-voicebot
```

---

## 2. Install Backend Dependencies

```bash
pip install -r backend/requirements.txt
```

---

## 3. Configure Environment Variables

Create a `.env` file inside the `backend` directory.

Example structure:

```text
DB_HOST=
DB_USER=
DB_PASSWORD=
DB_NAME=
VAPI_WEBHOOK_SECRET=
```

Sensitive credentials should never be committed to GitHub.

---

## 4. Start the FastAPI Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The backend will run at:

```text
http://127.0.0.1:8000
```

---

## 5. Start the Streamlit Dashboard

Open another terminal from the project root:

```bash
streamlit run dashboard/app.py
```

---

## 6. Start the Cloudflare Tunnel

```bash
cloudflared.exe tunnel --url http://localhost:8000
```

Configure the generated HTTPS URL as the webhook endpoint for the Vapi tools.

---

# Example Customer Portfolio

| Customer     | Loan Type     | Overdue Amount | Days Past Due | Risk   |
| ------------ | ------------- | -------------: | ------------: | ------ |
| Priya Kumar  | Home Loan     |        ₹24,500 |            25 | HIGH   |
| Arjun Reddy  | Auto Loan     |        ₹12,750 |            18 | MEDIUM |
| Rahul Sharma | Personal Loan |         ₹8,499 |            12 | LOW    |
| Sneha Patil  | Personal Loan |         ₹5,200 |             7 | LOW    |

---

# Tested Collection Outcomes

The system has been tested with collection workflows including:

- `PTP_AGREED`
- `ALREADY_PAID`
- `HARDSHIP_ESCALATED`
- `NO_RESPONSE`

The collection outcome, Promise-to-Pay information, and follow-up data are persisted in MySQL.

---

# Security

Sensitive configuration is managed using environment variables.

The following files are excluded from Git:

```text
.env
__pycache__/
*.pyc
```

Database credentials, API keys, and webhook secrets should never be committed to the repository.

---

# Project Outcome

This project demonstrates an end-to-end AI-powered collection workflow integrating:

- AI voice automation
- REST API development
- Business workflow management
- Relational database persistence
- Follow-up operations
- Customer risk prioritization
- Analytics and dashboard development

The project was designed to demonstrate how AI agents can automate business workflows while maintaining structured backend logic and persistent operational data.

---

# Author

**Karthik Hugar**
