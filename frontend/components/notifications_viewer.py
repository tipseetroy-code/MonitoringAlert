"""
Real-time notifications viewer for Streamlit UI
Displays notifications from the database
"""
import streamlit as st
import sqlite3
from datetime import datetime
from typing import List, Dict, Any
import os


def get_notifications(db_path: str = "/var/lib/sre-agent/sre_audit.db", limit: int = 50, unread_only: bool = False) -> List[Dict[str, Any]]:
    """Fetch notifications from database"""
    try:
        if not os.path.exists(db_path):
            return []
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """
            SELECT * FROM notifications
            WHERE 1=1
        """
        if unread_only:
            query += " AND read = 0"

        query += " ORDER BY created_at DESC LIMIT ?"

        cursor.execute(query, (limit,))
        rows = cursor.fetchall()

        notifications = [dict(row) for row in rows]
        conn.close()

        return notifications

    except Exception as e:
        st.error(f"Error fetching notifications: {e}")
        return []


def mark_notification_as_read(db_path: str, notification_id: int):
    """Mark a notification as read"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE notifications SET read = 1 WHERE id = ?", (notification_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Error marking notification as read: {e}")


def mark_all_notifications_as_read(db_path: str):
    """Mark all notifications as read"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE notifications SET read = 1 WHERE read = 0")
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Error marking all as read: {e}")


def get_severity_badge(severity: str) -> str:
    """Return colored badge HTML for severity"""
    colors = {
        "CRITICAL": "#dc2626",
        "HIGH": "#ea580c",
        "MEDIUM": "#ca8a04",
        "LOW": "#2563eb",
        "INFO": "#6b7280",
    }
    color = colors.get(severity, colors["INFO"])
    return f'<span style="background-color:{color};color:white;padding:4px 8px;border-radius:4px;font-size:12px;font-weight:bold;">{severity}</span>'


def get_notification_icon(notification_type: str) -> str:
    """Return emoji icon for notification type"""
    icons = {
        "incident_alert": "🚨",
        "resolution": "✅",
        "daily_report": "📊",
        "escalation": "⚠️",
    }
    return icons.get(notification_type, "📢")


def render_notifications_view(db_path: str = "/var/lib/sre-agent/sre_audit.db"):
    """Render the notifications view in Streamlit"""
    
    st.subheader("🔔 Real-Time Notifications")
    
    # Control bar
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        show_unread_only = st.checkbox("Show unread only", value=False)
    with col2:
        limit = st.selectbox("Show last", options=[10, 25, 50, 100, 500], index=2)
    with col3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    with col4:
        if st.button("✓ Mark all read", use_container_width=True):
            mark_all_notifications_as_read(db_path)
            st.success("All marked as read!")
            st.rerun()

    # Fetch notifications
    notifications = get_notifications(db_path, limit=limit, unread_only=show_unread_only)
    
    if not notifications:
        st.info("📭 No notifications to display. Notifications will appear here when incidents are detected or resolved.")
        return

    # Display unread count
    unread_count = sum(1 for n in notifications if not n.get("read", False))
    if unread_count > 0:
        st.warning(f"🔴 {unread_count} unread notification(s)")

    # Display notifications
    for notif in notifications:
        is_read = notif.get("read", False)
        bg_color = "#f9fafb" if is_read else "#eff6ff"
        border_color = "#e5e7eb" if is_read else "#3b82f6"
        
        with st.container():
            # Create notification card
            icon = get_notification_icon(notif.get("notification_type", ""))
            severity_badge = get_severity_badge(notif.get("severity", "INFO"))
            
            st.markdown(
                f"""
                <div style="background-color:{bg_color};border-left:4px solid {border_color};padding:16px;margin-bottom:12px;border-radius:4px;">
                    <div style="display:flex;align-items:center;justify-content:space-between;">
                        <div>
                            <span style="font-size:24px;margin-right:8px;">{icon}</span>
                            <strong style="font-size:16px;">{notif.get("title", "Notification")}</strong>
                        </div>
                        <div>
                            {severity_badge}
                        </div>
                    </div>
                    <p style="margin:8px 0;color:#374151;">{notif.get("message", "")}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            # Expandable details
            with st.expander(f"Details - {notif.get('created_at', '')}", expanded=False):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.text(f"ID: {notif.get('id')}")
                    st.text(f"Type: {notif.get('notification_type', 'N/A')}")
                    st.text(f"Incident ID: {notif.get('incident_id', 'N/A')}")
                with col_b:
                    st.text(f"Created: {notif.get('created_at', 'N/A')}")
                    st.text(f"Recipients: {notif.get('recipients', 'N/A')}")
                    st.text(f"Status: {'Read' if is_read else 'Unread'}")
                
                if notif.get("details"):
                    st.text_area("Additional Details", value=notif.get("details", ""), height=100, disabled=True)
                
                if not is_read:
                    if st.button(f"Mark as read", key=f"read_{notif.get('id')}"):
                        mark_notification_as_read(db_path, notif.get('id'))
                        st.success("Marked as read!")
                        st.rerun()

    # Summary stats
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Notifications", len(notifications))
    with col2:
        st.metric("Unread", unread_count)
    with col3:
        critical_count = sum(1 for n in notifications if n.get("severity") == "CRITICAL")
        st.metric("Critical", critical_count)
    with col4:
        resolved_count = sum(1 for n in notifications if n.get("notification_type") == "resolution")
        st.metric("Resolved", resolved_count)
