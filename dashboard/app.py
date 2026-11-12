
import streamlit as st
from api import (
    login,
    get_me,
    submit_ticket,
    get_ticket,
    list_tickets,
    get_stats
)
import pandas as pd
# ---------- Page Configuration ----------

st.set_page_config(
    page_title="OpsAgent | IT Helpdesk",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ---------- Custom Styling ----------

st.markdown(
    """
    <style>
    .main {
        background-color: #f8fafc;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    .hero {
        padding: 35px;
        border-radius: 16px;
        background: linear-gradient(120deg, #172554, #1e40af);
        color: white;
        margin-bottom: 25px;
    }

    .hero h1 {
    color: #ffffff !important;
    font-size: 40px !important;
    line-height: 1.2;
    margin: 0 0 12px 0;
    display: block;
    }
    .hero p {
        color: #dbeafe;
        font-size: 17px;
    }

    .feature-card {
        background: white;
        padding: 22px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        min-height: 175px;
    }

    .feature-card h3 {
        color: #1e3a8a;
    }
    .feature-card p {
    color: #475569 !important;
    font-size: 16px;
    line-height: 1.6;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ---------- Authentication ----------

if "access_token" not in st.session_state:

    st.title("OpsAgent Login")
    st.write("Sign in to access your IT helpdesk portal.")

    with st.form("login_form"):

        username_input = st.text_input(
            "Username",
            placeholder="Enter your username"
        )

        password_input = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password"
        )

        login_button = st.form_submit_button(
            "Login",
            type="primary",
            use_container_width=True
        )

    if login_button:

        if not username_input.strip() or not password_input:
            st.error("Please enter your username and password.")

        else:
            try:
                result = login(
                    username_input.strip(),
                    password_input
                )

                token = result["access_token"]
                profile = get_me(token)

                st.session_state["access_token"] = token
                st.session_state["current_user"] = profile

                st.rerun()

            except RuntimeError as e:
                st.error(str(e))

    st.stop()


# Validate the saved session on every rerun.

token = st.session_state["access_token"]

try:
    current_user = get_me(token)
    st.session_state["current_user"] = current_user

except RuntimeError:
    st.session_state.pop("access_token", None)
    st.session_state.pop("current_user", None)
    st.session_state.pop("last_ticket", None)
    st.session_state.pop("tracked_ticket", None)

    st.error("Your session expired or could not be verified. Please log in again.")
    st.stop()


# ---------- Sidebar Navigation ----------


# ---------- Sidebar Navigation ----------

with st.sidebar:

    st.title("🤖 OpsAgent")
    st.caption("AI-Powered IT Helpdesk")

    st.divider()

    st.write(f"Signed in as **{current_user['username']}**")
    st.caption(f"Role: {current_user['role'].capitalize()}")

    st.divider()

    if current_user["role"] == "admin":
        pages = [
            "Overview",
            "IT Admin Dashboard"
        ]
    else:
        pages = [
            "Overview",
            "Employee Portal"
        ]

    page = st.radio(
        "NAVIGATION",
        pages
    )

    st.divider()

    if st.button("Log out", use_container_width=True):

        for key in [
            "access_token",
            "current_user",
            "last_ticket",
            "tracked_ticket"
        ]:
            st.session_state.pop(key, None)

        st.rerun()

    st.divider()

    st.caption("Multi-Agent IT Helpdesk Automation")
    st.caption("Version 1.0")


# ---------- Overview Page ----------

if page == "Overview":

    st.markdown(
        """
        <div class="hero">
            <h1>Welcome to OpsAgent</h1>
            <p>
                Intelligent IT helpdesk automation powered by
                multi-agent artificial intelligence.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader("How OpsAgent works")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="feature-card">
                <h3>01. Triage Agent</h3>
                <p>
                    Analyses employee tickets and classifies
                    their category and urgency.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            """
            <div class="feature-card">
                <h3>02. Diagnostic Agent</h3>
                <p>
                    Investigates the reported issue and
                    identifies its probable cause.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            """
            <div class="feature-card">
                <h3>03. Resolution Agent</h3>
                <p>
                    Executes approved corrective actions,
                    verifies fixes and escalates failures.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    st.subheader("Get started")

    col1, col2 = st.columns(2)

    with col1:
        st.info(
            "**Employee Portal**\n\n"
            "Submit an IT support ticket and track its progress."
        )

    with col2:
        st.info(
            "**IT Admin Dashboard**\n\n"
            "Monitor tickets, agent activity and resolution statistics."
        )

    st.caption(
        "OpsAgent | Multi-Agent System for IT Helpdesk Automation"
    )


# ---------- Employee Portal ----------


elif page == "Employee Portal":

    st.title("Employee Portal")
    st.write("Submit and track your IT support tickets.")

    st.divider()

    # ---------- Submit a Ticket ----------

        # ---------- Submit a Ticket ----------

    st.subheader("Submit a New IT Ticket")

    with st.form("ticket_submission_form"):

        username = current_user["username"]

        st.text_input(
            "Employee Username",
            value=username,
            disabled=True
        )

        description = st.text_area(
            "Describe Your IT Issue",
            placeholder=(
                "Example: I cannot connect to the company VPN. "
                "It shows a gateway timeout error."
            ),
            height=150
        )

        submitted = st.form_submit_button(
            "Submit Ticket",
            type="primary",
            use_container_width=True
        )

    if submitted:

        if len(description.strip()) < 5:
            st.error("Please provide a more detailed issue description.")

        else:
            with st.spinner(
                "OpsAgent is analysing and processing your ticket..."
            ):
                try:
                    ticket = submit_ticket(
                        username,
                        description.strip(),
                        token
                    )

                    st.session_state["last_ticket"] = ticket

                except RuntimeError as e:
                    st.error(str(e))
# ---------- Display Submission Result ----------

    if "last_ticket" in st.session_state:

        submitted_ticket = st.session_state["last_ticket"]

        st.success("Your IT support ticket was submitted successfully!")

        st.write(
            f"**Ticket ID:** `{submitted_ticket.get('ticket_id', 'Unavailable')}`"
        )

        st.write(
            f"**Status:** {submitted_ticket.get('status', 'Unknown').upper()}"
        )

        st.info("Please save your Ticket ID to track your issue later.")
    # ---------- Track an Existing Ticket ----------

    st.divider()

    st.subheader("Track an Existing Ticket")

    track_id = st.text_input(
        "Enter your Ticket ID",
        placeholder="Example: a80880b8"
    )

    if st.button("Track Ticket", use_container_width=True):

        if not track_id.strip():
            st.warning("Please enter a ticket ID.")

        else:
            try:
                ticket = get_ticket(track_id.strip(),token)

                st.session_state["tracked_ticket"] = ticket

            except RuntimeError as e:
                st.session_state.pop("tracked_ticket", None)
                st.error(str(e))

    if "tracked_ticket" in st.session_state:

        tracked = st.session_state["tracked_ticket"]

        st.write(f"**Ticket ID:** `{tracked['ticket_id']}`")
        st.write(f"**Employee:** {tracked['username']}")
        st.write(f"**Description:** {tracked['description']}")

        st.write(
            f"**Status:** {tracked['status'].upper()}"
        )

        st.json({
            "triage": tracked.get("triage"),
            "diagnosis": tracked.get("diagnosis"),
            "resolution": tracked.get("resolution")
        })



# ---------- IT Admin Dashboard ----------


elif page == "IT Admin Dashboard":

    st.title("IT Admin Dashboard")
    st.write("Monitor tickets, AI agents and helpdesk performance.")

    # ---------- Fetch Live Data ----------

    try:
        stats = get_stats(token)
        tickets = list_tickets(token=token, limit=500)
    except RuntimeError as e:
        st.error(str(e))
        st.stop()

    st.divider()

    # ---------- KPI Cards ----------

    st.subheader("Helpdesk Overview")

    total = stats.get("total", 0)
    by_status = stats.get("by_status", {})
    resolved = by_status.get("resolved", 0)
    escalated = by_status.get("escalated", 0)
    open_tickets = by_status.get("open", 0)
    processing = by_status.get("processing", 0)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Tickets", total)
    col2.metric("Resolved", resolved)
    col3.metric("Escalated", escalated)
    col4.metric(
        "Resolution Rate",
        f"{stats.get('automated_resolution_rate', 0)}%"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Open", open_tickets)
    col2.metric("Processing", processing)
    col3.metric(
        "Average Processing Time",
        f"{stats.get('avg_response_seconds', 0)} sec"
    )

    st.divider()

    # ---------- Ticket Analytics ----------

    st.subheader("Ticket Analytics")

    chart1, chart2 = st.columns(2)

    with chart1:
        st.markdown("**Tickets by Category**")

        category_data = stats.get("by_category", {})

        if category_data:
            category_df = pd.DataFrame(
                list(category_data.items()),
                columns=["Category", "Tickets"]
            )

            st.bar_chart(
                category_df,
                x="Category",
                y="Tickets"
            )
        else:
            st.info("No category data available.")

    with chart2:
        st.markdown("**Tickets by Urgency**")

        urgency_data = stats.get("by_urgency", {})

        if urgency_data:
            urgency_df = pd.DataFrame(
                list(urgency_data.items()),
                columns=["Urgency", "Tickets"]
            )

            st.bar_chart(
                urgency_df,
                x="Urgency",
                y="Tickets"
            )
        else:
            st.info("No urgency data available.")

    st.divider()

    # ---------- Ticket Management ----------

    st.subheader("Ticket Management")

    status_options = [
        "All",
        "open",
        "processing",
        "resolved",
        "escalated"
    ]

    category_options = [
        "All",
        "VPN",
        "Account",
        "Disk",
        "Other"
    ]

    urgency_options = [
        "All",
        "Low",
        "Medium",
        "High"
    ]

    filter1, filter2, filter3 = st.columns(3)

    with filter1:
        selected_status = st.selectbox(
            "Filter by Status",
            status_options
        )

    with filter2:
        selected_category = st.selectbox(
            "Filter by Category",
            category_options
        )

    with filter3:
        selected_urgency = st.selectbox(
            "Filter by Urgency",
            urgency_options
        )

    filtered_tickets = tickets

    if selected_status != "All":
        filtered_tickets = [
            t for t in filtered_tickets
            if t.get("status") == selected_status
        ]

    if selected_category != "All":
        filtered_tickets = [
            t for t in filtered_tickets
            if (t.get("triage") or {}).get("category")
            == selected_category
        ]

    if selected_urgency != "All":
        filtered_tickets = [
            t for t in filtered_tickets
            if (t.get("triage") or {}).get("urgency")
            == selected_urgency
        ]

    if filtered_tickets:

        table_data = []

        for ticket in filtered_tickets:
            triage_data = ticket.get("triage") or {}

            table_data.append({
                "Ticket ID": ticket.get("ticket_id"),
                "Employee": ticket.get("username"),
                "Category": triage_data.get("category", "N/A"),
                "Urgency": triage_data.get("urgency", "N/A"),
                "Status": ticket.get("status"),
                "Processing Time (sec)": ticket.get(
                    "processing_seconds"
                )
            })

        st.dataframe(
            pd.DataFrame(table_data),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No tickets match the selected filters.")

    st.caption(
        f"Showing {len(filtered_tickets)} of "
        f"{len(tickets)} retrieved tickets."
    )

    st.divider()

    # ---------- Escalation Monitoring ----------

    st.subheader("Escalation Monitoring")

    escalated_tickets = [
        t for t in tickets
        if t.get("status") == "escalated"
    ]

    if escalated_tickets:

        st.warning(
            f"{len(escalated_tickets)} ticket(s) require human intervention."
        )

        for ticket in escalated_tickets:

            resolution_data = ticket.get("resolution") or {}

            with st.expander(
                f"{ticket['ticket_id']} — {ticket['username']}"
            ):
                st.write(
                    "**Description:**",
                    ticket.get("description")
                )

                st.write(
                    "**Reason:**",
                    resolution_data.get(
                        "escalation_reason",
                        "No escalation reason recorded."
                    )
                )

    else:
        st.success("No escalated tickets currently.")

    st.divider()

    # ---------- Individual Ticket Inspection ----------

    st.subheader("Inspect Ticket and Agent Activity")

    if tickets:

        ticket_ids = [
            ticket["ticket_id"]
            for ticket in tickets
        ]

        selected_ticket_id = st.selectbox(
            "Select a ticket",
            ticket_ids
        )

        selected_ticket = next(
            t for t in tickets
            if t["ticket_id"] == selected_ticket_id
        )

        st.markdown(
            f"**Employee:** {selected_ticket['username']}"
        )

        st.markdown(
            f"**Description:** {selected_ticket['description']}"
        )

        st.markdown(
            f"**Status:** {selected_ticket['status'].upper()}"
        )

        with st.expander("Complete Agent Results"):
            st.json({
                "triage": selected_ticket.get("triage"),
                "diagnosis": selected_ticket.get("diagnosis"),
                "resolution": selected_ticket.get("resolution")
            })

        with st.expander("Agent Activity Timeline"):

            for step in selected_ticket.get("trace", []):

                st.markdown(
                    f"**{step.get('agent', 'System').upper()}**"
                )

                st.write(step.get("summary", ""))
                st.caption(str(step.get("timestamp", "")))

                st.divider()

    else:
        st.info("No tickets available for inspection.")

    # ---------- Refresh Dashboard ----------

    st.divider()

    if st.button("Refresh Dashboard", use_container_width=True):
        st.rerun()
