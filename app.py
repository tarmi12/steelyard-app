import streamlit as st

st.set_page_config(page_title="ลานเหล็กไทย", page_icon="🏗️", layout="wide")

# ---- Session State ----
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None

# ---- ค่าเริ่มต้นสำหรับตั้งค่าระบบ (หากยังไม่เคยตั้ง) ----
if "transit_loss_pct" not in st.session_state:
    st.session_state.transit_loss_pct = 0.5
if "transit_loss_kg" not in st.session_state:
    st.session_state.transit_loss_kg = 50
if "penalty_rate_per_kg" not in st.session_state:
    st.session_state.penalty_rate_per_kg = 10.0
if "freight_flat_rate" not in st.session_state:
    st.session_state.freight_flat_rate = 3000.0
if "freight_per_ton_rate" not in st.session_state:
    st.session_state.freight_per_ton_rate = 100.0
if "default_base_weight" not in st.session_state:
    st.session_state.default_base_weight = "ต้นทาง"

# ---- ค่าเกี่ยวกับ Google Drive / LINE (ใหม่) ----
if "google_drive_folder_id" not in st.session_state:
    st.session_state.google_drive_folder_id = ""
if "line_channel_token" not in st.session_state:
    st.session_state.line_channel_token = ""
if "line_oa_url" not in st.session_state:
    st.session_state.line_oa_url = "https://line.me/R/ti/p/@your_bot_id"  # เปลี่ยนตามจริง

# ---- หน้า Login (จำลอง) ----
def login():
    st.title("🔐 เข้าสู่ระบบ - ลานเหล็กไทย")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🧑‍💼 เจ้าของ", use_container_width=True):
            st.session_state.role = "owner"
            st.session_state.user = {"display_name": "เจ้าของ"}
            st.rerun()
    with col2:
        if st.button("👨‍💼 ผู้จัดการ", use_container_width=True):
            st.session_state.role = "manager"
            st.session_state.user = {"display_name": "ผู้จัดการ"}
            st.rerun()
    with col3:
        if st.button("🧾 เสมียน", use_container_width=True):
            st.session_state.role = "clerk"
            st.session_state.user = {"display_name": "เสมียน"}
            st.rerun()

if not st.session_state.user:
    login()
    st.stop()

# ---- Navigation ----
role = st.session_state.role
pages = []

if role in ["clerk", "manager", "owner"]:
    pages += [
        st.Page("pages/purchase_entry.py", title="บันทึกซื้อเข้าสิ้นวัน", icon="📥"),
        st.Page("pages/purchase_history.py", title="ประวัติการซื้อ", icon="📋"),
        st.Page("pages/load_order.py", title="สั่งโหลด (จองคิว)", icon="🚚"),
        st.Page("pages/weigh_out.py", title="ชั่งออก (Weigh Out)", icon="⚖️"),
        st.Page("pages/destination_scan.py", title="สแกนหลักฐานปลายทาง", icon="📸"),
        st.Page("pages/sales_clearing.py", title="เคลียร์บิลปลายทาง", icon="💰"),
        st.Page("pages/stock_balance.py", title="สต็อกคงเหลือ", icon="📦"),
        st.Page("pages/truck_management.py", title="จัดการรถ/คนขับ", icon="🚘"),
    ]
if role in ["clerk", "manager"]:
    pages += [
        st.Page("pages/receipt_entry.py", title="บันทึกเงินโอน", icon="💵"),
        st.Page("pages/freight_payment.py", title="จ่ายค่าขนส่ง", icon="🚛"),
    ]
if role in ["manager", "owner"]:
    pages += [
        st.Page("pages/manual_adjustment.py", title="ปรับยอดสต็อกด้วยมือ", icon="🔧"),
        st.Page("pages/dashboard.py", title="แดชบอร์ด", icon="📊"),
        st.Page("pages/report_sales.py", title="รายงานการขาย/กำไร/ภาษี", icon="📈"),
        st.Page("pages/report_freight.py", title="รายงานค่าขนส่ง/ค่าปรับ", icon="📉"),
        st.Page("pages/report_debtors.py", title="รายงานสถานะลูกหนี้-เจ้าหนี้", icon="📑"),
    ]
if role == "owner":
    pages += [
        st.Page("pages/settings.py", title="ตั้งค่าระบบ", icon="⚙️"),
        st.Page("pages/user_management.py", title="จัดการผู้ใช้", icon="👥"),
    ]

pg = st.navigation(pages)
pg.run()