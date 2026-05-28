import streamlit as st

# ========== ตั้งค่าหน้า ==========
st.set_page_config(page_title="ลานเหล็กไทย", page_icon="🏗️", layout="wide")

# ========== Session State ==========
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None

# ========== หน้า Login จำลอง ==========
def login():
    st.title("🔐 เข้าสู่ระบบ - ลานเหล็กไทย")
    st.markdown("---")
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

# ========== ถ้ายังไม่ login ==========
if not st.session_state.user:
    login()
    st.stop()

# ========== สร้าง Navigation ตาม Role ==========
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

# ========== แสดง Sidebar และ เนื้อหาหน้าที่เลือก ==========
pg = st.navigation(pages)
pg.run()