import streamlit as st
import requests
import pandas as pd

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Kapture Collection Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("Kapture Finance Collection Dashboard")
st.caption("AI Voice Collection & Recovery Analytics")

try:
    analytics_response = requests.get(
        f"{API_URL}/analytics",
        timeout=5
    )

    calls_response = requests.get(
        f"{API_URL}/calls",
        timeout=5
    )

    analytics_response.raise_for_status()
    calls_response.raise_for_status()

    analytics = analytics_response.json()
    calls_data = calls_response.json()

except requests.RequestException:
    st.error(
        "Unable to connect to the FastAPI backend. "
        "Make sure the backend is running on port 8000."
    )
    st.stop()


# -------------------------
# KPI CARDS
# -------------------------

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


st.divider()


# -------------------------
# COLLECTION SUMMARY
# -------------------------

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


st.divider()


# -------------------------
# RECENT CALLS
# -------------------------

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

# -------------------------
# CALL DETAILS
# -------------------------

st.divider()

st.subheader("Call Details")

if calls:

    call_options = {
        f"{call['customer_name']} | {call['disposition']} | {call['call_id'][:8]}...":
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
                st.write(f"₹{ptp_amount:,.2f}")
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
        st.info(call_detail["notes"] or "No notes available.")

    except requests.RequestException:

        st.error(
            "Unable to retrieve call details from the backend."
        )

st.caption(
    "Data source: FastAPI REST API → MySQL"
)