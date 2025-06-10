import requests
import streamlit as st

API_BASE = "http://api:8000"

st.set_page_config(page_title="AInsight Admin", page_icon="🧠", layout="wide")
st.title("🧠 AInsight Admin Panel")

tab_members, tab_digests, tab_trigger = st.tabs(["👥 Team Members", "📰 Digests", "🚀 Run"])

# --- Team Members ---
with tab_members:
    st.header("Team Members")

    # Add new member
    with st.expander("➕ Add New Member"):
        with st.form("add_member"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            topics = st.text_input("Topics (comma-separated)", placeholder="NLP, CV, LLMs")
            submitted = st.form_submit_button("Add Member")
            if submitted and name and email:
                topic_list = [t.strip() for t in topics.split(",") if t.strip()]
                resp = requests.post(f"{API_BASE}/members", json={
                    "name": name, "email": email, "topics": topic_list,
                }, timeout=10)
                if resp.status_code == 200:
                    st.success(f"Added {name}")
                    st.rerun()
                else:
                    st.error(resp.json().get("detail", "Failed to add member"))

    # List members
    try:
        members = requests.get(f"{API_BASE}/members", timeout=10).json()
    except Exception:
        members = []
        st.warning("Cannot connect to API server")

    if members:
        for m in members:
            col1, col2, col3, col4 = st.columns([3, 3, 2, 2])
            col1.write(f"**{m['name']}**")
            col2.write(m["email"])
            status = "✅ Active" if m["active"] else "❌ Inactive"
            col3.write(status)
            if col4.button("Toggle", key=f"toggle_{m['id']}"):
                requests.patch(f"{API_BASE}/members/{m['id']}/toggle", timeout=10)
                st.rerun()
    else:
        st.info("No team members yet. Add one above.")

# --- Digests ---
with tab_digests:
    st.header("Past Digests")

    try:
        digests = requests.get(f"{API_BASE}/digests?limit=20", timeout=10).json()
    except Exception:
        digests = []
        st.warning("Cannot connect to API server")

    if digests:
        for d in digests:
            with st.expander(f"📅 {d['date']} — {d.get('paper_count', '?')} papers"):
                detail = requests.get(f"{API_BASE}/digests/{d['id']}", timeout=10).json()
                st.html(detail.get("html_content", "<p>No content</p>"))

                if detail.get("send_log"):
                    st.subheader("Delivery Status")
                    for log in detail["send_log"]:
                        icon = "✅" if log["status"] == "sent" else "❌"
                        st.write(f"{icon} Member #{log['member_id']} — {log['status']}")
                        if log.get("error"):
                            st.caption(f"Error: {log['error']}")
    else:
        st.info("No digests yet. Trigger a run to generate one.")

# --- Manual Trigger ---
with tab_trigger:
    st.header("Manual Run")
    st.write("Trigger the digest workflow manually. This will search for papers, "
             "summarize them, and send the digest email to all active team members.")

    if st.button("🚀 Run Digest Now", type="primary"):
        with st.spinner("Workflow running..."):
            try:
                resp = requests.post(f"{API_BASE}/run", timeout=10)
                if resp.status_code == 200:
                    st.success("Workflow triggered! Check the Digests tab in a few minutes.")
                else:
                    st.error("Failed to trigger workflow")
            except Exception as e:
                st.error(f"Cannot connect to API: {e}")
