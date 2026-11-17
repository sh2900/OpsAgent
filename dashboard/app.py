
import importlib
import streamlit as st
import api
importlib.reload(api)

from api import (
    login,
    register_user,
    reset_password_request,
    get_me,
    submit_ticket,
    get_ticket,
    update_ticket_admin,
    create_employee_user,
    list_tickets,
    get_stats,
    get_sim_scenarios,
    get_sim_state,
    set_sim_scenario,
    reset_sim_scenario,
    seed_demo_tickets
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
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Metric Cards Styling */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
        transition: all 0.25s ease-in-out;
        min-height: 105px;
    }

    div[data-testid="stMetric"]:hover {
        border-color: rgba(59, 130, 246, 0.5);
        transform: translateY(-2px);
        box-shadow: 0 8px 16px -2px rgba(0, 0, 0, 0.15);
    }

    div[data-testid="stMetric"] label {
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #94a3b8 !important;
    }

    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.85rem !important;
        font-weight: 700 !important;
    }

    /* Card Panels & Containers */
    .hero {
        padding: 35px;
        border-radius: 16px;
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #2563eb 100%);
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.3);
    }

    .hero h1 {
        color: #ffffff !important;
        font-size: 38px !important;
        font-weight: 700 !important;
        line-height: 1.2;
        margin: 0 0 10px 0;
    }

    .hero p {
        color: #dbeafe !important;
        font-size: 16px;
        margin: 0;
    }

    .feature-card {
        background: rgba(255, 255, 255, 0.03);
        padding: 24px;
        border-radius: 14px;
        border: 1px solid rgba(148, 163, 184, 0.2);
        min-height: 180px;
        transition: all 0.2s ease;
    }

    .feature-card:hover {
        border-color: rgba(59, 130, 246, 0.4);
        transform: translateY(-3px);
    }

    .feature-card h3 {
        color: #60a5fa !important;
        font-size: 1.2rem;
        margin-top: 0;
    }

    .feature-card p {
        color: #94a3b8 !important;
        font-size: 0.95rem;
        line-height: 1.6;
    }

    /* Forms & Inputs */
    div[data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 14px;
        padding: 24px;
    }

    /* Tabs Styling */
    button[data-baseweb="tab"] {
        font-size: 1rem;
        font-weight: 600;
        padding: 10px 20px;
    }

    /* Primary Buttons */
    div.stButton > button[kind="primary"] {
        border-radius: 8px;
        font-weight: 600;
        padding: 0.55rem 1.4rem;
        letter-spacing: 0.02em;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ---------- Authentication ----------

if "access_token" not in st.session_state:

    st.title("OpsAgent Portal")
    st.write("Sign in, create an account, or reset your password.")

    tab_login, tab_register, tab_forgot = st.tabs([
        "🔐 Sign In",
        "📝 Create Account",
        "🔑 Forgot Password"
    ])

    with tab_login:
        with st.form("login_form"):

            username_input = st.text_input(
                "Username",
                placeholder="Enter your username",
                key="login_user"
            )

            password_input = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
                key="login_pass"
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

    with tab_register:
        st.subheader("Create an Employee Account")
        st.caption("Register for access to submit and track IT support tickets.")

        with st.form("register_form"):

            reg_username = st.text_input(
                "Choose Username",
                placeholder="e.g., john_smith",
                key="reg_user"
            )

            reg_password = st.text_input(
                "Create Password (min 12 characters)",
                type="password",
                placeholder="Enter a secure password",
                key="reg_pass"
            )

            reg_confirm = st.text_input(
                "Confirm Password",
                type="password",
                placeholder="Re-enter your password",
                key="reg_confirm"
            )

            register_button = st.form_submit_button(
                "Register Account",
                type="primary",
                use_container_width=True
            )

        if register_button:

            if not reg_username.strip():
                st.error("Please enter a username.")
            elif len(reg_password) < 12:
                st.error("Password must be at least 12 characters long.")
            elif reg_password != reg_confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    res = register_user(reg_username.strip(), reg_password)
                    st.success(
                        f"Account '{res.get('username')}' registered successfully! "
                        "Please switch to the 'Sign In' tab to log in."
                    )
                except RuntimeError as e:
                    st.error(str(e))

    with tab_forgot:
        st.subheader("Reset Password")
        st.caption("Self-service credential recovery for your IT helpdesk account.")

        with st.form("forgot_password_form"):

            forgot_username = st.text_input(
                "Username",
                placeholder="Enter your registered username",
                key="forgot_user"
            )

            forgot_new_pass = st.text_input(
                "New Password (min 12 characters)",
                type="password",
                placeholder="Enter new password",
                key="forgot_pass"
            )

            forgot_confirm = st.text_input(
                "Confirm New Password",
                type="password",
                placeholder="Re-enter new password",
                key="forgot_confirm"
            )

            reset_button = st.form_submit_button(
                "Reset Password",
                type="primary",
                use_container_width=True
            )

        if reset_button:

            if not forgot_username.strip():
                st.error("Please enter your username.")
            elif len(forgot_new_pass) < 12:
                st.error("New password must be at least 12 characters long.")
            elif forgot_new_pass != forgot_confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    res = reset_password_request(forgot_username.strip(), forgot_new_pass)
                    st.success(
                        f"Password for '{forgot_username}' reset successfully! "
                        "Please switch to the 'Sign In' tab to log in with your new password."
                    )
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
            "IT Admin Dashboard",
            "User Management"
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


# ---------- Shared Component: Ticket Information & Escalation Dossier ----------

def render_ticket_dossier(
    ticket: dict,
    is_admin: bool = False,
    token: str = "",
    form_prefix: str = ""
):
    """
    Renders comprehensive, user-friendly details for any ticket:
    - Current status & post-escalation state
    - Identified problem, category, urgency, and technical diagnosis
    - Reason for human escalation and required technician action
    - Human or automated resolution details and notes
    - Complete agent activity audit trail
    """
    status = ticket.get("status", "unknown").lower()
    tid = ticket.get("ticket_id", "N/A")
    triage = ticket.get("triage") or {}
    diagnosis = ticket.get("diagnosis") or {}
    resolution = ticket.get("resolution") or {}
    admin_notes = ticket.get("admin_notes")
    resolved_by = ticket.get("resolved_by")
    resolved_at = ticket.get("resolved_at")
    escalated_at = ticket.get("escalated_at")

    # 1. Status Header
    if status == "resolved":
        if resolved_by:
            st.success(f"### Status: RESOLVED (Human Fix Applied)")
            st.caption(f"Resolved by Administrator **{resolved_by}**")
        else:
            st.success("### Status: AUTO-RESOLVED (Fixed by AI Agent)")
            st.caption("Predefined corrective fix successfully verified by automated agents.")
    elif status == "escalated":
        st.warning("### Status: ESCALATED (Pending Human IT Support Review)")
        st.caption("AI agents diagnosed the issue and flagged it for human IT administrator intervention.")
    elif status == "closed":
        st.info("### Status: CLOSED")
    else:
        st.info(f"### Status: {status.upper()}")

    # 2. Key Metrics Bar
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ticket ID", tid)
    col1.caption(f"Employee: **{ticket.get('username', 'N/A')}**")

    col2.metric("Category", triage.get("category", "N/A"))
    col2.caption(f"Urgency: **{triage.get('urgency', 'N/A')}**")

    service_name = diagnosis.get("service", triage.get("category", "N/A"))
    service_status = diagnosis.get("service_status", "unknown")
    col3.metric("Service", service_name)
    col3.caption(f"State: `{service_status}`")

    proc_time = ticket.get("processing_seconds")
    col4.metric("AI Processing Time", f"{proc_time}s" if proc_time else "N/A")

    st.markdown("---")

    # 3. Problem Diagnosis Details
    st.markdown("#### 🔍 Problem Diagnosis & Evidence")
    prob_col1, prob_col2 = st.columns(2)
    with prob_col1:
        st.markdown(f"**Reported Issue:**\n> {ticket.get('description', '')}")
        if ticket.get("attachment_name"):
            kb = round((ticket.get("attachment_size") or 0) / 1024, 1)
            st.markdown(f"📎 **Attachment:** `{ticket['attachment_name']}` ({kb} KB)")
        if triage.get("reasoning"):
            st.markdown(f"**Triage Assessment:** {triage.get('reasoning')}")
    with prob_col2:
        st.markdown(f"**Diagnosed Root Cause:**\n> {diagnosis.get('probable_cause', 'Under investigation')}")
        if diagnosis.get("details"):
            with st.expander("Diagnostic Telemetry Data"):
                st.json(diagnosis.get("details"))

    st.markdown("---")

    # 4. Escalation & Post-Escalation Resolution Information
    st.markdown("#### 📋 Escalation & Resolution Information")

    if status == "escalated":
        esc_reason = (
            resolution.get("escalation_reason")
            or diagnosis.get("probable_cause")
            or "Automated fix not permitted or unavailable."
        )
        st.error(f"**Reason for Human Escalation:**\n\n{esc_reason}")

        st.info(
            "**Required Information & Next Steps:**\n\n"
            "• **Problem Assessment:** The diagnosed issue cannot be safely resolved by predefined automation scripts.\n"
            "• **Action Required:** An IT administrator must manually review credentials, certificates, or backend systems.\n"
            f"• **Current Stage:** Queued for human administrator review (Escalated: {escalated_at or ticket.get('updated_at', 'Recently')})."
        )

        if is_admin and token:
            st.markdown("##### 🛠️ Human-in-the-Loop Administrator Resolution")
            with st.form(f"{form_prefix}resolve_dossier_form_{tid}"):
                admin_action = st.selectbox(
                    "Target Status",
                    options=["resolved", "closed"],
                    key=f"{form_prefix}dossier_status_{tid}"
                )
                admin_comment = st.text_area(
                    "Admin Resolution Notes / Corrective Actions Taken",
                    placeholder="Describe how the problem was resolved (e.g., Renewed certificate in Active Directory, cleared disk storage manually, rebooted gateway).",
                    key=f"{form_prefix}dossier_comment_{tid}"
                )
                submit_resolve = st.form_submit_button(
                    "Submit Human Resolution",
                    type="primary"
                )

            if submit_resolve:
                if not admin_comment.strip():
                    st.error("Please enter resolution notes before submitting.")
                else:
                    try:
                        update_ticket_admin(
                            tid,
                            admin_action,
                            admin_comment.strip(),
                            token
                        )
                        st.success(f"Ticket {tid} marked as {admin_action} successfully!")
                        st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))

    elif status in {"resolved", "closed"} and admin_notes:
        st.success(
            f"**✅ Post-Escalation Resolution (Human Fix Applied):**\n\n"
            f"• **Resolution Handled By:** `{resolved_by or 'IT Admin'}`\n\n"
            f"• **Actions Taken:** {admin_notes}\n\n"
            f"• **Resolution Timestamp:** {resolved_at or ticket.get('updated_at', 'Recently')}"
        )
    elif status == "resolved":
        action_name = resolution.get("action_taken", "Predefined automated fix")
        st.success(
            f"**✅ Automated AI Resolution:**\n\n"
            f"• **Remediation Action:** `{action_name}`\n\n"
            f"• **Outcome:** {resolution.get('message', 'Fix applied and verified successfully.')}\n\n"
            f"• **Verification Status:** Verified service returned to expected healthy operational state."
        )

    # 5. Activity Timeline / Trace
    with st.expander("📜 Full Ticket Audit Trail & Agent Activity"):
        for step in ticket.get("trace", []):
            st.markdown(f"**[{step.get('agent', 'System').upper()}]** {step.get('summary', '')}")
            if step.get("data"):
                st.caption(f"Details: {step.get('data')}")
            st.caption(f"Timestamp: {step.get('timestamp', '')}")
            st.divider()


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

        uploaded_file = st.file_uploader(
            "Attach error screenshot or log file (optional)",
            type=["png", "jpg", "jpeg", "log", "txt", "pdf"]
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
                    att_name = uploaded_file.name if uploaded_file else None
                    att_size = uploaded_file.size if uploaded_file else None
                    ticket = submit_ticket(
                        username,
                        description.strip(),
                        token,
                        attachment_name=att_name,
                        attachment_size=att_size
                    )

                    st.session_state["last_ticket"] = ticket

                except RuntimeError as e:
                    st.error(str(e))
# ---------- Display Submission Result ----------

    if "last_ticket" in st.session_state:

        submitted_ticket = st.session_state["last_ticket"]
        st.subheader("Your Submitted Ticket")
        render_ticket_dossier(submitted_ticket, is_admin=False, form_prefix="sub_")
        st.info("💡 Please save your Ticket ID above to track your issue later.")
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
        st.subheader("Tracked Ticket Details")
        render_ticket_dossier(tracked, is_admin=False, form_prefix="trk_")



# ---------- IT Admin Dashboard ----------


elif page == "IT Admin Dashboard":

    dash_col1, dash_col2 = st.columns([3, 1])
    with dash_col1:
        st.title("IT Admin Dashboard")
        st.write("Monitor tickets, AI agents and helpdesk performance.")
    with dash_col2:
        st.write("")
        auto_refresh = st.checkbox("🔄 Live Tracker (10s)", value=False, key="auto_refresh_toggle")

    # ---------- Demo Mode / Simulation Controls (Collapsed for Presentation) ----------

    with st.expander("🛠️ Simulation Lab / Demo Scenarios (Testing Controls)", expanded=False):
        st.caption(
            "Configure simulated IT failures for demonstrating "
            "OpsAgent's automated troubleshooting and escalation workflows."
        )

        # Display success message after applying/resetting a scenario
        if "demo_mode_notice" in st.session_state:
            st.success(st.session_state.pop("demo_mode_notice"))

        SCENARIO_LABELS = {
            "healthy": "Healthy Environment",
            "vpn_down": "VPN Unavailable",
            "vpn_cert_expired": "Expired VPN Certificate",
            "account_locked": "Locked Account (Alice)",
            "password_expired": "Expired Password (Bob)",
            "account_disabled_by_hr": "Account Disabled by HR",
            "disk_full": "Disk Full",
            "disk_full_unfixable": "Disk Full - Cleanup Fails",
            "multi_failure": "Multiple Simultaneous Failures"
        }

        try:
            demo_info = get_sim_scenarios()
            demo_state = get_sim_state()

            available_scenarios = demo_info.get("available", [])
            current_scenario = demo_info.get("current", "healthy")

            if available_scenarios:
                current_index = (
                    available_scenarios.index(current_scenario)
                    if current_scenario in available_scenarios
                    else 0
                )

                col1, col2 = st.columns([3, 1])

                with col1:
                    selected_scenario = st.selectbox(
                        "Choose a demo scenario",
                        options=available_scenarios,
                        index=current_index,
                        format_func=lambda x: SCENARIO_LABELS.get(x, x),
                        key="demo_scenario_selector"
                    )

                with col2:
                    st.write("")
                    st.write("")
                    st.info(
                        f"Active: {SCENARIO_LABELS.get(current_scenario, current_scenario)}"
                    )

                col1, col2, col3 = st.columns(3)

                with col1:
                    if st.button(
                        "Apply Scenario",
                        use_container_width=True,
                        type="primary"
                    ):
                        result = set_sim_scenario(selected_scenario)
                        st.session_state["demo_mode_notice"] = (
                            f"Scenario applied: "
                            f"{SCENARIO_LABELS.get(selected_scenario, selected_scenario)}"
                        )
                        st.rerun()

                with col2:
                    if st.button(
                        "Reset to Healthy",
                        use_container_width=True
                    ):
                        reset_sim_scenario()
                        st.session_state["demo_mode_notice"] = (
                            "Simulator restored to a healthy environment."
                        )
                        st.rerun()

                with col3:
                    if st.button(
                        "🌱 Seed Demo Tickets",
                        use_container_width=True
                    ):
                        try:
                            seed_res = seed_demo_tickets(token)
                            st.session_state["demo_mode_notice"] = seed_res.get(
                                "message", "Demo tickets seeded successfully."
                            )
                        except RuntimeError as e:
                            st.session_state["demo_mode_notice"] = f"Failed to seed demo tickets: {e}"
                        st.rerun()

                with st.expander("View Simulated Environment State"):
                    st.json(demo_state.get("state", {}))

        except RuntimeError as e:
            st.warning(f"Demo Mode unavailable: {e}")

    st.divider()

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
    resolution_rate = stats.get("automated_resolution_rate", 0)
    escalation_rate = stats.get("escalation_rate", 0)
    avg_seconds = stats.get("avg_response_seconds", 0)

    # Row 1: Volume & Resolution Metrics (4 Equal Columns)
    r1_col1, r1_col2, r1_col3, r1_col4 = st.columns(4)
    r1_col1.metric("Total Tickets", total)
    r1_col2.metric("Resolved", resolved)
    r1_col3.metric("Escalated", escalated)
    r1_col4.metric("Resolution Rate", f"{resolution_rate}%")

    st.write("")  # Visual row separator for uniform grid

    # Row 2: Queue & Performance Metrics (4 Perfectly Aligned Columns)
    r2_col1, r2_col2, r2_col3, r2_col4 = st.columns(4)
    r2_col1.metric("Open Queue", open_tickets)
    r2_col2.metric("Processing", processing)
    r2_col3.metric("Escalation Rate", f"{escalation_rate}%")
    r2_col4.metric("Avg Processing Time", f"{avg_seconds} sec")

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

            tid = ticket['ticket_id']

            with st.expander(
                f"🚨 {tid} — {ticket['username']} ({ticket.get('description', '')[:50]}...)"
            ):
                render_ticket_dossier(ticket, is_admin=True, token=token, form_prefix=f"esc_{tid}_")

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
            "Select a ticket to inspect",
            ticket_ids
        )

        selected_ticket = next(
            t for t in tickets
            if t["ticket_id"] == selected_ticket_id
        )

        render_ticket_dossier(
            selected_ticket,
            is_admin=True,
            token=token,
            form_prefix=f"insp_{selected_ticket['ticket_id']}_"
        )

    else:
        st.info("No tickets available for inspection.")

    # ---------- Refresh Dashboard ----------

    st.divider()

    if st.button("Refresh Dashboard", use_container_width=True):
        st.rerun()

    if auto_refresh:
        import time
        st.caption("🟢 Live tracker active: auto-refreshing every 10 seconds...")
        time.sleep(10)
        st.rerun()


# ---------- User Management Page (Admin) ----------

elif page == "User Management" and current_user["role"] == "admin":

    st.title("User Management")
    st.write("Provision new employee accounts for the IT Helpdesk.")

    st.divider()

    st.subheader("Create Employee Account")

    with st.form("create_employee_form"):
        new_username = st.text_input(
            "Employee Username",
            placeholder="e.g., john_doe"
        )
        new_password = st.text_input(
            "Initial Password (min 12 characters)",
            type="password",
            placeholder="Enter secure initial password"
        )

        submit_user = st.form_submit_button(
            "Create Account",
            type="primary",
            use_container_width=True
        )

    if submit_user:
        if not new_username.strip() or len(new_password) < 12:
            st.error("Please enter a valid username and a password of at least 12 characters.")
        else:
            try:
                result = create_employee_user(
                    new_username.strip(),
                    new_password,
                    token
                )
                st.success(f"Employee account '{result.get('username')}' created successfully!")
            except RuntimeError as e:
                st.error(str(e))
