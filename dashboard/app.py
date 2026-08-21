import streamlit as st
import requests
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Kapture Collection Dashboard",
    page_icon="📊",
    layout="wide"
)


# ============================================================
# HEADER
# ============================================================

st.title("Kapture Finance Collection Dashboard")
st.caption("AI Voice Collection & Recovery Analytics")


# ============================================================
# FETCH DATA FROM FASTAPI
# ============================================================

try:

    analytics_response = requests.get(
        f"{API_URL}/analytics",
        timeout=5
    )

    customers_response = requests.get(
        f"{API_URL}/customers",
        timeout=5
    )

    calls_response = requests.get(
        f"{API_URL}/calls",
        timeout=5
    )

    followups_response = requests.get(
        f"{API_URL}/followups",
        timeout=5
    )

    due_followups_response = requests.get(
        f"{API_URL}/followups/due",
        timeout=5
    )

    analytics_response.raise_for_status()
    customers_response.raise_for_status()
    calls_response.raise_for_status()
    followups_response.raise_for_status()
    due_followups_response.raise_for_status()

    analytics = analytics_response.json()
    customers_data = customers_response.json()
    calls_data = calls_response.json()
    followups_data = followups_response.json()
    due_followups_data = due_followups_response.json()

except requests.RequestException:

    st.error(
        "Unable to connect to the FastAPI backend. "
        "Make sure the backend is running on port 8000."
    )

    st.stop()


# ============================================================
# KPI CARDS
# ============================================================

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total Calls",
    analytics["total_calls"]
)

col2.metric(
    "PTP Agreed",
    analytics["ptp_agreed"]
)

col3.metric(
    "Already Paid",
    analytics["already_paid"]
)

col4.metric(
    "Hardship Cases",
    analytics["hardship_escalated"]
)


# ============================================================
# COLLECTION SUMMARY
# ============================================================

st.divider()

col1, col2 = st.columns(2)

with col1:

    st.subheader("Collection Summary")

    st.metric(
        "No Response",
        analytics["no_response"]
    )

    st.metric(
        "Total Promised Amount",
        f"₹{analytics['total_ptp_amount']:,.2f}"
    )


with col2:

    st.subheader("Disposition Breakdown")

    chart_data = pd.DataFrame({
        "Disposition": [
            "PTP Agreed",
            "Already Paid",
            "Hardship",
            "No Response"
        ],
        "Calls": [
            analytics["ptp_agreed"],
            analytics["already_paid"],
            analytics["hardship_escalated"],
            analytics["no_response"]
        ]
    })

    chart_data = chart_data.set_index("Disposition")

    st.bar_chart(chart_data)


# ============================================================
# COLLECTION CALL HISTORY
# ============================================================

st.divider()

st.subheader("Collection Call History")

calls = calls_data.get("calls", [])

if calls:

    df = pd.DataFrame(calls)

    display_columns = [
        "call_id",
        "customer_name",
        "account_id",
        "disposition",
        "ptp_amount",
        "ptp_date",
        "created_at"
    ]

    available_columns = [
        column
        for column in display_columns
        if column in df.columns
    ]

    st.dataframe(
        df[available_columns],
        use_container_width=True,
        hide_index=True
    )

else:

    st.info("No collection calls found.")


# ============================================================
# CALL DETAILS
# ============================================================

st.divider()

st.subheader("Call Details")

if calls:

    call_options = {
        f"{call['customer_name']} | "
        f"{call['disposition']} | "
        f"{call['call_id'][:8]}...":
        call["call_id"]
        for call in calls
    }

    selected_label = st.selectbox(
        "Select a collection call",
        options=list(call_options.keys())
    )

    selected_call_id = call_options[selected_label]

    try:

        detail_response = requests.get(
            f"{API_URL}/calls/{selected_call_id}",
            timeout=5
        )

        detail_response.raise_for_status()

        call_detail = detail_response.json()

        col1, col2, col3 = st.columns(3)

        with col1:

            st.write("**Customer**")
            st.write(call_detail["customer_name"])

            st.write("**Account ID**")
            st.write(call_detail["account_id"])

            st.write("**Loan Type**")
            st.write(call_detail["loan_type"])

        with col2:

            st.write("**Overdue Amount**")

            st.write(
                f"₹{call_detail['overdue_amount']:,.2f}"
            )

            st.write("**Days Past Due**")
            st.write(call_detail["days_past_due"])

            st.write("**Disposition**")
            st.write(call_detail["disposition"])

        with col3:

            st.write("**PTP Amount**")

            ptp_amount = call_detail["ptp_amount"]

            if ptp_amount is not None:

                st.write(
                    f"₹{ptp_amount:,.2f}"
                )

            else:

                st.write("N/A")

            st.write("**PTP Date**")

            st.write(
                call_detail["ptp_date"]
                if call_detail["ptp_date"]
                else "N/A"
            )

            st.write("**Verification**")

            st.write(
                "Verified"
                if call_detail["verification_status"]
                else "Not Verified"
            )

        st.write("**Call Notes**")

        st.info(
            call_detail["notes"]
            or "No notes available."
        )

    except requests.RequestException:

        st.error(
            "Unable to retrieve call details from the backend."
        )


# ============================================================
# FOLLOW-UP MANAGEMENT
# ============================================================

st.divider()

st.subheader("Follow-up Management")

due_followups = due_followups_data.get(
    "followups",
    []
)

pending_followups = followups_data.get(
    "followups",
    [])


# -------------------------
# FOLLOW-UP COUNTERS
# -------------------------

col1, col2 = st.columns(2)

with col1:

    st.metric(
        "Due Follow-ups",
        due_followups_data.get(
            "total_due",
            0
        )
    )

with col2:

    st.metric(
        "Pending Follow-ups",
        followups_data.get(
            "total_followups",
            0
        )
    )


# -------------------------
# DUE FOLLOW-UPS
# -------------------------

if due_followups:

    st.warning(
        "Follow-ups requiring attention today"
    )

    due_df = pd.DataFrame(
        due_followups
    )

    due_columns = [
        "customer_name",
        "account_id",
        "ptp_amount",
        "ptp_date",
        "follow_up_date",
        "attempt_count"
    ]

    available_columns = [
        column
        for column in due_columns
        if column in due_df.columns
    ]

    st.dataframe(
        due_df[available_columns],
        use_container_width=True,
        hide_index=True
    )

else:

    st.success(
        "No follow-ups are due today."
    )


# ============================================================
# PENDING FOLLOW-UP ACTIONS
# ============================================================

st.subheader("Pending Follow-ups")

if pending_followups:

    for followup in pending_followups:

        customer_name = followup["customer_name"]

        call_id = followup["call_id"]

        amount = followup["ptp_amount"]

        follow_up_date = followup[
            "follow_up_date"
        ]

        attempts = followup[
            "attempt_count"
        ]

        st.write(
            f"**{customer_name}** | "
            f"₹{amount:,.2f} | "
            f"Follow-up: {follow_up_date} | "
            f"Attempts: {attempts}"
        )

        col1, col2 = st.columns(2)

        # -------------------------
        # COMPLETE
        # -------------------------

        with col1:

            if st.button(
                "Complete",
                key=f"complete_{call_id}"
            ):

                try:

                    response = requests.put(
                        f"{API_URL}/followups/{call_id}",
                        params={
                            "status": "COMPLETED",
                            "increment_attempt": True
                        },
                        timeout=5
                    )

                    response.raise_for_status()

                    st.success(
                        "Follow-up marked as completed."
                    )

                    st.rerun()

                except requests.RequestException:

                    st.error(
                        "Failed to update follow-up."
                    )

        # -------------------------
        # MARK FAILED
        # -------------------------

        with col2:

            if st.button(
                "Mark Failed",
                key=f"failed_{call_id}"
            ):

                try:

                    response = requests.put(
                        f"{API_URL}/followups/{call_id}",
                        params={
                            "status": "FAILED",
                            "increment_attempt": True
                        },
                        timeout=5
                    )

                    response.raise_for_status()

                    st.warning(
                        "Follow-up marked as failed."
                    )

                    st.rerun()

                except requests.RequestException:

                    st.error(
                        "Failed to update follow-up."
                    )

        st.divider()

else:

    st.info(
        "No pending follow-ups."
    )


# ============================================================
# CUSTOMER PORTFOLIO
# ============================================================

st.divider()

st.subheader("Customer Portfolio")

customers = customers_data.get(
    "customers",
    []
)

if customers:

    customers_df = pd.DataFrame(
        customers
    )

    # -------------------------
    # PORTFOLIO METRICS
    # -------------------------

    total_customers = len(customers_df)

    total_overdue = customers_df[
        "overdue_amount"
    ].sum()

    high_risk_customers = len(
        customers_df[
            customers_df["risk_level"] == "HIGH"
        ]
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Total Customers",
            total_customers
        )

    with col2:

        st.metric(
            "Total Overdue Amount",
            f"₹{total_overdue:,.2f}"
        )

    with col3:

        st.metric(
            "High Risk Customers",
            high_risk_customers
        )

    st.write("")

    # -------------------------
    # RISK DISTRIBUTION
    # -------------------------

    st.subheader("Risk Distribution")

    risk_counts = (
        customers_df["risk_level"]
        .value_counts()
        .reindex(
            ["HIGH", "MEDIUM", "LOW"],
            fill_value=0
        )
    )

    risk_chart = pd.DataFrame({
        "Customers": risk_counts
    })

    st.bar_chart(risk_chart)

    # -------------------------
    # CUSTOMER TABLE
    # -------------------------

    st.subheader("Customer Details")

    portfolio_columns = [
        "customer_name",
        "account_id",
        "loan_type",
        "overdue_amount",
        "days_past_due",
        "risk_level"
    ]

    available_columns = [
        column
        for column in portfolio_columns
        if column in customers_df.columns
    ]

    st.dataframe(
        customers_df[available_columns],
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "No customers found."
    )


# ============================================================
# FOOTER
# ============================================================

st.caption(
    "Data source: FastAPI REST API → MySQL"
)