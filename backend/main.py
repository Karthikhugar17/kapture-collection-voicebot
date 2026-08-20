from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Any, Dict
import json
import os
import uuid
import secrets
import mysql.connector
from mysql.connector import Error

from dotenv import load_dotenv

load_dotenv()

VAPI_WEBHOOK_SECRET = os.getenv("VAPI_WEBHOOK_SECRET")

# ============================================================
# MYSQL DATABASE CONNECTION
# ============================================================

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            port=int(os.getenv("MYSQL_PORT", 3306)),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE")
        )

        return connection

    except Error as error:
        print(f"[DATABASE ERROR] {error}")
        return None
    

def get_customer_id(account_id: str):
    connection = get_db_connection()

    if connection is None:
        return None

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id
            FROM customers
            WHERE account_id = %s
            """,
            (account_id,)
        )

        row = cursor.fetchone()

        cursor.close()
        connection.close()

        return row[0] if row else None

    except Error as error:

        print(f"[DATABASE ERROR] Customer ID lookup failed: {error}")

        if connection.is_connected():
            connection.close()

        return None

def update_verification_status(
    call_id: str,
    verified: bool
):
    connection = get_db_connection()

    if connection is None:
        return False

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE collection_calls
            SET verification_status = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE call_id = %s
            """,
            (verified, call_id)
        )

        connection.commit()

        cursor.close()
        connection.close()

        return True

    except Error as error:

        print(
            f"[DATABASE ERROR] Verification update failed: {error}"
        )

        if connection.is_connected():
            connection.rollback()
            connection.close()

        return False
    
def update_ptp_record(
    call_id: str,
    amount: float,
    ptp_date: str
):
    connection = get_db_connection()

    if connection is None:
        return False

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE collection_calls
            SET ptp_amount = %s,
                ptp_date = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE call_id = %s
            """,
            (amount, ptp_date, call_id)
        )

        connection.commit()

        cursor.close()
        connection.close()

        return True

    except Error as error:

        print(
            f"[DATABASE ERROR] PTP update failed: {error}"
        )

        if connection.is_connected():
            connection.rollback()
            connection.close()

        return False

def update_disposition_record(
    call_id: str,
    status: str,
    notes: str
):
    connection = get_db_connection()

    if connection is None:
        return False

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE collection_calls
            SET disposition = %s,
                notes = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE call_id = %s
            """,
            (status, notes, call_id)
        )

        connection.commit()

        cursor.close()
        connection.close()

        return True

    except Error as error:

        print(
            f"[DATABASE ERROR] Disposition update failed: {error}"
        )

        if connection.is_connected():
            connection.rollback()
            connection.close()

        return False

def create_call_record(
    call_id: str,
    customer_id: int
):
    connection = get_db_connection()

    if connection is None:
        return False

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO collection_calls (
                call_id,
                customer_id
            )
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE
                updated_at = CURRENT_TIMESTAMP
            """,
            (call_id, customer_id)
        )

        connection.commit()

        cursor.close()
        connection.close()

        return True

    except Error as error:

        print(
            f"[DATABASE ERROR] Call record creation failed: {error}"
        )

        if connection.is_connected():
            connection.rollback()
            connection.close()

        return False

# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Kapture Finance Collections Backend",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================
#
# This is useful while testing through browser-based tools.
# Vapi server-to-server requests do not depend on browser CORS,
# but enabling it makes local testing easier.


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# MOCK CUSTOMER DATABASE
# ============================================================
#
# For the assessment/demo we use an in-memory customer.
#
# Customer:
#   Name: Rahul Sharma
#   Verification Code: 1234
#
# IMPORTANT:
# The name must be "Rahul Sharma", not just "Rahul".
#

CUSTOMERS = {
    "ACC-88392": {
        "customer_name": "Rahul Sharma",
        "verification_code": "1234",
        "loan_type": "Personal Loan",
        "overdue_amount": 8499,
        "days_past_due": 12,
        "phone": "+91XXXXXXXXXX"
    }
}


# ============================================================
# CALL STATE
# ============================================================
#
# In production this should be Redis / PostgreSQL / another
# persistent database.
#
# For the assessment, an in-memory dictionary is enough.
#

CALL_STATES: Dict[str, Dict[str, Any]] = {}


def get_call_state(call_id: str) -> Dict[str, Any]:
    """
    Get the current state of a call.
    If the call does not exist yet, initialize it.
    """

    if call_id not in CALL_STATES:

        CALL_STATES[call_id] = {
            "state": "AUTH_PENDING",
            "authenticated": False,
            "disposition": None,
            "ptp": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    return CALL_STATES[call_id]


# ============================================================
# HELPER: SAFE JSON
# ============================================================

def json_result(data: Dict[str, Any]) -> str:
    """
    Convert a Python dictionary into a JSON string.

    Vapi expects the 'result' field to be a string.
    """

    return json.dumps(
        data,
        ensure_ascii=False
    )


# ============================================================
# VERIFY CUSTOMER
# ============================================================

def verify_customer(
    call_id: str,
    customer_name: str,
    verification_code: str
) -> Dict[str, Any]:

    state = get_call_state(call_id)

    connection = get_db_connection()

    if connection is None:
        return {
            "verified": False,
            "reason": "Customer database is unavailable."
        }

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                account_id,
                customer_name,
                verification_code,
                loan_type,
                overdue_amount,
                days_past_due,
                phone
            FROM customers
            WHERE account_id = %s
            """,
            ("ACC-88392",)
        )

        customer = cursor.fetchone()

        cursor.close()
        connection.close()

    except Error as error:

        print(f"[DATABASE ERROR] Customer lookup failed: {error}")

        if connection.is_connected():
            connection.close()

        return {
            "verified": False,
            "reason": "Unable to access customer information."
        }

    if customer is None:

        return {
            "verified": False,
            "reason": "Customer account was not found."
        }

    # --------------------------------------------------------
    # Do not allow verification after call has ended
    # --------------------------------------------------------

    if state["state"] == "CALL_ENDED":

        return {
            "verified": False,
            "reason": "Call has already ended."
        }

    # --------------------------------------------------------
    # Validate input
    # --------------------------------------------------------

    customer_name = str(customer_name or "").strip()
    verification_code = str(verification_code or "").strip()

    if not customer_name:
        return {
            "verified": False,
            "reason": "Customer name is required."
        }

    if not verification_code:
        return {
            "verified": False,
            "reason": "Verification code is required."
        }

    # --------------------------------------------------------
    # Compare name
    # --------------------------------------------------------

    name_matches = (
        customer_name.lower()
        == customer["customer_name"].lower()
    )

    # --------------------------------------------------------
    # Compare verification code
    # --------------------------------------------------------

    code_matches = (
        verification_code
        == customer["verification_code"]
    )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    if name_matches and code_matches:

        state["authenticated"] = True
        state["state"] = "AUTHENTICATED"

        customer_id = get_customer_id(
            customer["account_id"]
        )

        if customer_id is not None:

            create_call_record(
                call_id=call_id,
                customer_id=customer_id
            )

            update_verification_status(
                call_id=call_id,
                verified=True
            )

        return {
            "verified": True,
            "customer_name": customer["customer_name"],
            "message": "Identity verified successfully."
        }

    # --------------------------------------------------------
    # FAILURE
    # --------------------------------------------------------

    state["authenticated"] = False

    customer_id = get_customer_id(
        customer["account_id"]
    )

    if customer_id is not None:

        create_call_record(
            call_id=call_id,
            customer_id=customer_id
        )

        update_verification_status(
            call_id=call_id,
            verified=False
        )

    return {
        "verified": False,
        "message": "Identity could not be verified."
    }


# ============================================================
# GET ACCOUNT DETAILS
# ============================================================

def get_account_details(
    call_id: str
) -> Dict[str, Any]:

    state = get_call_state(call_id)

    # --------------------------------------------------------
    # SECURITY GATE
    # --------------------------------------------------------

    if not state["authenticated"]:

        return {
            "allowed": False,
            "reason": (
                "Customer must be authenticated before "
                "account information can be disclosed."
            )
        }

    connection = get_db_connection()

    if connection is None:
        return {
            "allowed": False,
            "reason": "Customer database is unavailable."
        }

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                customer_name,
                loan_type,
                overdue_amount,
                days_past_due
            FROM customers
            WHERE account_id = %s
            """,
            ("ACC-88392",)
        )

        customer = cursor.fetchone()

        cursor.close()
        connection.close()

    except Error as error:

        print(f"[DATABASE ERROR] Account lookup failed: {error}")

        if connection.is_connected():
            connection.close()

        return {
            "allowed": False,
            "reason": "Unable to retrieve account information."
        }

    if customer is None:

        return {
            "allowed": False,
            "reason": "Customer account was not found."
        }

    state["state"] = "NEGOTIATION"

    return {
        "allowed": True,
        "customer_name": customer["customer_name"],
        "loan_type": customer["loan_type"],
        "overdue_amount": float(customer["overdue_amount"]),
        "days_past_due": customer["days_past_due"]
    }


# ============================================================
# LOG PROMISE TO PAY
# ============================================================

def log_promise_to_pay(
    call_id: str,
    amount: float,
    ptp_date: str
) -> Dict[str, Any]:

    state = get_call_state(call_id)

    # --------------------------------------------------------
    # SECURITY GATE
    # --------------------------------------------------------

    if not state["authenticated"]:

        return {
            "success": False,
            "reason": (
                "Customer must be authenticated before "
                "recording a payment commitment."
            )
        }

    # --------------------------------------------------------
    # Validate amount
    # --------------------------------------------------------

    try:
        amount = float(amount)
    except (TypeError, ValueError):

        return {
            "success": False,
            "reason": "Payment amount must be a valid number."
        }

    if amount <= 0:

        return {
            "success": False,
            "reason": "Payment amount must be greater than zero."
        }

    # --------------------------------------------------------
    # Validate and normalize date
    # --------------------------------------------------------

    ptp_date = str(ptp_date or "").strip()

    if not ptp_date:

        return {
            "success": False,
            "reason": "Promise-to-pay date is required."
        }

    # Use India local date for relative dates such as "tomorrow"
    today = datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).date()

    normalized_date = None

    # --------------------------------------------------------
    # Handle relative dates
    # --------------------------------------------------------

    date_text = ptp_date.lower().strip()

    if date_text == "today":

        normalized_date = today

    elif date_text == "tomorrow":

        normalized_date = today + timedelta(days=1)

    elif date_text in (
        "day after tomorrow",
        "day after tommorow"
    ):

        normalized_date = today + timedelta(days=2)

    # --------------------------------------------------------
    # Handle exact YYYY-MM-DD dates
    # --------------------------------------------------------

    if normalized_date is None:

        try:

            normalized_date = datetime.strptime(
                ptp_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            return {
                "success": False,
                "reason": (
                    "Promise-to-pay date must be an exact "
                    "YYYY-MM-DD date or a supported relative "
                    "date such as today or tomorrow."
                )
            }

    # --------------------------------------------------------
    # Prevent past dates
    # --------------------------------------------------------

    if normalized_date < today:

        return {
            "success": False,
            "reason": (
                "Promise-to-pay date cannot be in the past."
            )
        }

    # Convert to YYYY-MM-DD for storage
    ptp_date = normalized_date.isoformat()

    # --------------------------------------------------------
    # Create PTP ID
    # --------------------------------------------------------

    ptp_id = (
        "PTP-"
        + str(uuid.uuid4())[:8].upper()
    )

    state["ptp"] = {
        "amount": amount,
        "date": ptp_date,
        "ptp_id": ptp_id
    }

    database_updated = update_ptp_record(
        call_id=call_id,
        amount=amount,
        ptp_date=ptp_date
    )

    if not database_updated:

        print(
            "[DATABASE WARNING] "
            "PTP could not be persisted to MySQL."
        )

    state["state"] = "RESOLUTION"

    return {
        "success": True,
        "ptp_id": ptp_id,
        "amount": amount,
        "ptp_date": ptp_date
    }


# ============================================================
# SEND PAYMENT LINK
# ============================================================

def send_payment_link(
    call_id: str,
    channel: str
) -> Dict[str, Any]:

    state = get_call_state(call_id)

    # --------------------------------------------------------
    # SECURITY GATE
    # --------------------------------------------------------

    if not state["authenticated"]:

        return {
            "success": False,
            "reason": (
                "Customer must be authenticated before "
                "sending a payment link."
            )
        }

    channel = str(channel or "").strip()

    # --------------------------------------------------------
    # Validate channel
    # --------------------------------------------------------

    if channel not in ["SMS", "WhatsApp"]:

        return {
            "success": False,
            "reason": (
                "Unsupported payment-link channel. "
                "Use SMS or WhatsApp."
            )
        }

    # --------------------------------------------------------
    # Mock payment link
    # --------------------------------------------------------

    payment_link = (
        "https://pay.kapture.example/ACC-88392"
    )

    return {
        "success": True,
        "channel": channel,
        "link_sent": True,
        "payment_link": payment_link
    }


# ============================================================
# MARK DISPOSITION
# ============================================================

def mark_disposition(
    call_id: str,
    status: str,
    notes: str = ""
) -> Dict[str, Any]:

    state = get_call_state(call_id)

    status = str(status or "").strip()

    allowed_statuses = [
        "PTP_AGREED",
        "ALREADY_PAID",
        "DISPUTED",
        "HARDSHIP_ESCALATED",
        "WRONG_PERSON",
        "DO_NOT_CALL",
        "NO_RESPONSE",
        "AUTH_FAILED"
    ]

    # --------------------------------------------------------
    # Validate status
    # --------------------------------------------------------

    if status not in allowed_statuses:

        return {
            "success": False,
            "reason": (
                "Invalid disposition. "
                f"Allowed values: {', '.join(allowed_statuses)}"
            )
        }

    # --------------------------------------------------------
    # Save disposition
    # --------------------------------------------------------

    notes = str(notes or "")

    state["disposition"] = {
        "status": status,
        "notes": notes,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat()
    }

    database_updated = update_disposition_record(
        call_id=call_id,
        status=status,
        notes=notes
    )

    if not database_updated:

        print(
            "[DATABASE WARNING] "
            "Disposition could not be persisted to MySQL."
        )

    state["state"] = "CALL_ENDED"

    return {
        "success": True,
        "disposition": status,
        "message": (
            "Call disposition recorded successfully."
        )
    }


# ============================================================
# ESCALATE TO HUMAN
# ============================================================

def escalate_to_agent(
    call_id: str,
    reason: str
) -> Dict[str, Any]:

    state = get_call_state(call_id)

    # --------------------------------------------------------
    # SECURITY GATE
    # --------------------------------------------------------

    if not state["authenticated"]:

        return {
            "success": False,
            "reason": (
                "Customer must be authenticated before "
                "account-specific escalation."
            )
        }

    reason = str(reason or "").strip()

    if not reason:

        return {
            "success": False,
            "reason": "Escalation reason is required."
        }

    state["state"] = "RESOLUTION"

    return {
        "success": True,
        "escalated": True,
        "reason": reason,
        "message": (
            "The case has been marked for human follow-up."
        )
    }


# ============================================================
# TOOL DISPATCHER
# ============================================================
#
# This function receives a Vapi tool name and its parameters,
# then calls the appropriate backend function.
#

def execute_tool(
    tool_name: str,
    parameters: Dict[str, Any],
    call_id: str
) -> Dict[str, Any]:

    # --------------------------------------------------------
    # VERIFY CUSTOMER
    # --------------------------------------------------------

    if tool_name == "verify_customer":

        return verify_customer(
            call_id=call_id,
            customer_name=parameters.get(
                "customer_name",
                ""
            ),
            verification_code=parameters.get(
                "verification_code",
                ""
            )
        )

    # --------------------------------------------------------
    # GET ACCOUNT DETAILS
    # --------------------------------------------------------

    if tool_name == "get_account_details":

        return get_account_details(
            call_id=call_id
        )

    # --------------------------------------------------------
    # LOG PROMISE TO PAY
    # --------------------------------------------------------

    if tool_name == "log_promise_to_pay":

        return log_promise_to_pay(
            call_id=call_id,
            amount=parameters.get(
                "amount",
                0
            ),
            ptp_date=parameters.get(
                "ptp_date",
                ""
            )
        )

    # --------------------------------------------------------
    # SEND PAYMENT LINK
    # --------------------------------------------------------

    if tool_name == "send_payment_link":

        return send_payment_link(
            call_id=call_id,
            channel=parameters.get(
                "channel",
                ""
            )
        )

    # --------------------------------------------------------
    # MARK DISPOSITION
    # --------------------------------------------------------

    if tool_name == "mark_disposition":

        return mark_disposition(
            call_id=call_id,
            status=parameters.get(
                "status",
                ""
            ),
            notes=parameters.get(
                "notes",
                ""
            )
        )

    # --------------------------------------------------------
    # ESCALATE TO AGENT
    # --------------------------------------------------------

    if tool_name == "escalate_to_agent":

        return escalate_to_agent(
            call_id=call_id,
            reason=parameters.get(
                "reason",
                ""
            )
        )

    # --------------------------------------------------------
    # UNKNOWN TOOL
    # --------------------------------------------------------

    return {
        "success": False,
        "reason": f"Unknown tool: {tool_name}"
    }


# ============================================================
# VAPI WEBHOOK
# ============================================================
#
# Vapi sends tool calls to this endpoint.
#
# Current Vapi format is approximately:
#
# {
#   "message": {
#       "type": "tool-calls",
#       "call": {
#           "id": "..."
#       },
#       "toolCallList": [
#           {
#               "id": "...",
#               "name": "verify_customer",
#               "parameters": {
#                   "customer_name": "Rahul Sharma",
#                   "verification_code": "1234"
#               }
#           }
#       ]
#   }
# }
#
# Vapi expects:
#
# {
#   "results": [
#       {
#           "toolCallId": "...",
#           "result": "..."
#       }
#   ]
# }
#
# ============================================================

@app.post("/webhook")
async def vapi_webhook(request: Request):

    # --------------------------------------------------------
    # Read raw JSON body
    # --------------------------------------------------------

    if not VAPI_WEBHOOK_SECRET:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Webhook authentication is not configured."
            }
        )

    provided_secret = request.headers.get("X-Vapi-Secret")

    if (
        not provided_secret
        or not secrets.compare_digest(
            provided_secret,
            VAPI_WEBHOOK_SECRET
        )
    ):
        return JSONResponse(
            status_code=401,
            content={
                "error": "Unauthorized."
            }
        )

    try:

        body = await request.json()

    except Exception:

        return JSONResponse(
            status_code=400,
            content={
                "error": "Request body must contain valid JSON."
            }
        )

    print("\n==================================================")
    print("[WEBHOOK] Request received")
    print(json.dumps(body, indent=2))
    print("==================================================")

    # ========================================================
    # DIRECT TEST MODE
    # ========================================================
    #
    # Vapi's Test Tool may send the function parameters
    # directly when testing a custom tool.
    #
    # Example:
    #
    # {
    #     "customer_name": "Rahul Sharma",
    #     "verification_code": "1234"
    # }
    #
    # Supporting this also makes local testing easy.
    #

    if (
        "customer_name" in body
        and "verification_code" in body
        and "message" not in body
    ):

        print("[WEBHOOK] Direct tool test detected")

        result = verify_customer(
            call_id="test-call",
            customer_name=body.get(
                "customer_name",
                ""
            ),
            verification_code=body.get(
                "verification_code",
                ""
            )
        )

        print(
            "[WEBHOOK] Direct test result:",
            result
        )

        return JSONResponse(
            status_code=200,
            content=result
        )

    # ========================================================
    # VAPI MESSAGE
    # ========================================================

    message = body.get(
        "message",
        {}
    )

    # --------------------------------------------------------
    # If message is missing
    # --------------------------------------------------------

    if not isinstance(message, dict):

        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid Vapi request: message must be an object."
            }
        )

    message_type = message.get(
        "type"
    )

    print(
        f"[WEBHOOK] Message type: {message_type}"
    )

    # ========================================================
    # NON TOOL-CALL EVENTS
    # ========================================================
    #
    # Vapi can send other server events.
    # We acknowledge them with HTTP 200.
    #

    if message_type != "tool-calls":

        print(
            "[WEBHOOK] Non-tool event acknowledged."
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "acknowledged",
                "message_type": message_type
            }
        )

    # ========================================================
    # GET TOOL CALL LIST
    # ========================================================

    tool_calls = message.get(
        "toolCallList",
        []
    )

    if not tool_calls:

        print(
            "[WEBHOOK] No tool calls found."
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "no_tool_calls",
                "results": []
            }
        )

    # ========================================================
    # GET CALL ID
    # ========================================================

    call = message.get(
        "call",
        {}
    )

    if isinstance(call, dict):

        call_id = call.get(
            "id",
            "unknown-call"
        )

    else:

        call_id = "unknown-call"

    print(
        f"[WEBHOOK] Call ID: {call_id}"
    )

    # ========================================================
    # PROCESS TOOL CALLS
    # ========================================================

    results = []

    for tool_call in tool_calls:

        try:

            # ------------------------------------------------
            # Tool call ID
            # ------------------------------------------------

            tool_call_id = tool_call.get(
                "id"
            )

            # ------------------------------------------------
            # Tool name
            # ------------------------------------------------

            tool_name = tool_call.get(
                "name"
            )

            # ------------------------------------------------
            # Parameters
            # ------------------------------------------------
            #
            # Current Vapi format uses "parameters".
            #
            # We also support "arguments" for compatibility
            # with other function-call formats.
            #

            parameters = tool_call.get(
                "parameters"
            )

            if parameters is None:

                parameters = tool_call.get(
                    "arguments",
                    {}
                )

            # ------------------------------------------------
            # Some payloads may put function details inside
            # a nested "function" object.
            # ------------------------------------------------

            function_data = tool_call.get(
                "function",
                {}
            )

            if isinstance(function_data, dict):

                if not tool_name:

                    tool_name = function_data.get(
                        "name"
                    )

                if not parameters:

                    parameters = function_data.get(
                        "arguments",
                        {}
                    )

            # ------------------------------------------------
            # Make sure parameters are a dictionary
            # ------------------------------------------------

            if parameters is None:

                parameters = {}

            if isinstance(parameters, str):

                try:

                    parameters = json.loads(
                        parameters
                    )

                except json.JSONDecodeError:

                    parameters = {}

            if not isinstance(parameters, dict):

                parameters = {}

            # ------------------------------------------------
            # Log tool call
            # ------------------------------------------------

            print(
                "\n[VAPI TOOL CALL]"
            )

            print(
                f"  Call ID     : {call_id}"
            )

            print(
                f"  Tool Call ID: {tool_call_id}"
            )

            print(
                f"  Tool Name   : {tool_name}"
            )

            print(
                f"  Parameters  : {parameters}"
            )

            # ------------------------------------------------
            # Validate tool name
            # ------------------------------------------------

            if not tool_name:

                result = {
                    "success": False,
                    "reason": "Tool name is missing."
                }

            elif not tool_call_id:

                result = {
                    "success": False,
                    "reason": "Tool call ID is missing."
                }

            else:

                # --------------------------------------------
                # Execute actual backend function
                # --------------------------------------------

                result = execute_tool(
                    tool_name=tool_name,
                    parameters=parameters,
                    call_id=call_id
                )

            # ------------------------------------------------
            # Vapi requires result to be a STRING
            # ------------------------------------------------

            results.append(
                {
                    "toolCallId": tool_call_id,
                    "result": json_result(result)
                }
            )

            print(
                f"[VAPI RESULT] {result}"
            )

        except Exception as error:

            print(
                f"[ERROR] Tool execution failed: {error}"
            )

            results.append(
                {
                    "toolCallId": tool_call.get(
                        "id"
                    ),
                    "error": "Tool execution failed."
                }
            )

    # ========================================================
    # RETURN RESULTS TO VAPI
    # ========================================================

    response = {
        "results": results
    }

    print(
        "\n[VAPI RESPONSE]"
    )

    print(
        json.dumps(
            response,
            indent=2
        )
    )

    return JSONResponse(
        status_code=200,
        content=response
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def health_check():

    return {
        "service": "Kapture Finance Collections Backend",
        "status": "running"
    }


# ============================================================
# OPTIONAL DEBUG ENDPOINT
# ============================================================
#
# Useful for seeing the current in-memory call state while
# developing.
#
# Example:
# http://127.0.0.1:8000/debug/call/test-call
#

@app.get("/debug/call/{call_id}")
def debug_call_state(call_id: str):

    state = CALL_STATES.get(
        call_id
    )

    if state is None:

        return {
            "call_id": call_id,
            "exists": False
        }

    return {
        "call_id": call_id,
        "exists": True,
        "state": state
    }

# ============================================================
# DATABASE HEALTH CHECK
# ============================================================

@app.get("/health/db")
def database_health_check():

    connection = get_db_connection()

    if connection is None:
        return {
            "database": "kapture_finance",
            "status": "disconnected"
        }

    try:

        cursor = connection.cursor()

        cursor.execute("SELECT 1")

        result = cursor.fetchone()

        cursor.close()
        connection.close()

        if result == (1,):

            return {
                "database": "kapture_finance",
                "status": "connected"
            }

        return {
            "database": "kapture_finance",
            "status": "error"
        }

    except Error as error:

        if connection.is_connected():
            connection.close()

        return {
            "database": "kapture_finance",
            "status": "error",
            "message": str(error)
        }