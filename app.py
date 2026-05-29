import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="ลานเหล็กไทย V2.6", page_icon="🏗️", layout="wide")

# ---- เชื่อมต่อฐานข้อมูล Supabase ----
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# ---- จัดเก็บข้อมูลเซสชันผู้ใช้งาน ----
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "role" not in st.session_state:
    st.session_state.role = None
if "display_name" not in st.session_state:
    st.session_state.display_name = None

# ---- ดึงค่าการตั้งค่าจากฐานข้อมูลจริงมาเก็บในแอปพลิเคชัน ----
if "settings_loaded" not in st.session_state:
    try:
        settings_res = supabase.table("system_settings").select("*").execute()
        for setting in settings_res.data:
            st.session_state[setting["key"]] = setting["value"]
        st.session_state.settings_loaded = True
    except Exception:
        st.session_state.transit_loss_threshold_percent = "0.5"
        st.session_state.transit_loss_threshold_kg = "50"
        st.session_state.penalty_rate_per_kg = "10.0"

# ---- ระบบเข้าสู่ระบบจริงผ่าน Supabase Profiles ----
def login_interface():
    st.title("🔐 เข้าสู่ระบบ - ลานเหล็กไทย V2.6")
    st.write("กรุณาเลือกบัญชีผู้ใช้ของคุณเพื่อเริ่มต้นระบบ (สิทธิ์ระบบจะถูกจัดสรรตามตำแหน่งในตาราง profiles)")
    
    try:
        profiles_res = supabase.table("profiles").select("*").execute()
        profiles = profiles_res.data
        
        if not profiles:
            st.warning("⚠️ ไม่พบข้อมูลผู้ใช้งานในตาราง profiles กรุณาเพิ่มข้อมูลผู้ใช้ในระบบหลังบ้านก่อน")
            return

        options = {f"{p['display_name']} ({p['role']})": p for p in profiles}
        selected_user_label = st.selectbox("เลือกบัญชีผู้ใช้ของคุณเพื่อลงชื่อเข้าใช้", list(options.keys()))
        
        if st.button("เข้าสู่ระบบ", use_container_width=True):
            user_data = options[selected_user_label]
            st.session_state.user_id = user_data["id"]
            st.session_state.role = user_data["role"]
            st.session_state.display_name = user_data["display_name"]
            st.rerun()
            
    except Exception as e:
        st.error(f"ไม่สามารถดึงข้อมูลผู้ใช้งานได้: {e}")

if not st.session_state.user_id:
    login_interface()
    st.stop()

# ---- ระบบแสดงเมนูตามระดับสิทธิ์ (Dynamic Navigation) ----
role = st.session_state.role
pages = []

# ⭐ เคสที่ 1: สิทธิ์ของ "admin" (เจ้าของลาน) เข้าได้ทุกหน้าจอ 100%
if role == "admin":
    pages += [
        # --- หมวดหมู่งานหน้าร้านและการขนส่ง ---
        st.Page("pages/purchase_entry.py", title="บันทึกซื้อเข้าสิ้นวัน", icon="📥"),
        st.Page("pages/purchase_history.py", title="ประวัติการซื้อ", icon="📋"),
        st.Page("pages/load_order.py", title="สั่งโหลด (จองคิว)", icon="🚚"),
        st.Page("pages/weigh_out.py", title="ชั่งออก (Weigh Out)", icon="⚖️"),
        st.Page("pages/truck_monitor_report.py", title="🎛️ ติดตามสถานะรถวิ่งงานสด", icon="🎯"),  # แทรกตรงนี้เรียบร้อยครับ
        st.Page("pages/destination_scan.py", title="สแกนหลักฐานปลายทาง", icon="📸"),
        st.Page("pages/sales_clearing.py", title="เคลียร์บิลปลายทาง", icon="💰"),
        st.Page("pages/stock_balance.py", title="สต็อกคงเหลือ", icon="📦"),
        st.Page("pages/truck_management.py", title="จัดการรถ/คนขับ", icon="🚘"),
        
        # --- หมวดหมู่งานธุรกรรมการเงิน ---
        st.Page("pages/receipt_entry.py", title="บันทึกเงินโอน", icon="💵"),
        st.Page("pages/freight_payment.py", title="จ่ายค่าขนส่ง", icon="🚛"),
        
        # --- หมวดหมู่งานบริหารและรายงานขั้นสูง ---
        st.Page("pages/manual_adjustment.py", title="ปรับยอดสต็อกด้วยมือ", icon="🔧"),
        st.Page("pages/dashboard.py", title="แดชบอร์ดผู้บริหาร", icon="📊"),
        st.Page("pages/report_sales.py", title="รายงานการขาย/กำไร/ภาษี", icon="📈"),
        st.Page("pages/report_freight.py", title="รายงานค่าขนส่ง/ค่าปรับ", icon="📉"),
        st.Page("pages/report_debtors.py", title="รายงานสถานะลูกหนี้-เจ้าหนี้", icon="📑"),
        
        # --- หมวดหมู่ควบคุมระบบนโยบาย ---
        st.Page("pages/settings.py", title="ตั้งค่าระบบ", icon="⚙️"),
        st.Page("pages/user_management.py", title="จัดการผู้ใช้", icon="👥"),
    ]

# 💼 เคสที่ 2: สิทธิ์ของผู้จัดการ (manager)
elif role == "manager":
    pages += [
        st.Page("pages/purchase_entry.py", title="บันทึกซื้อเข้าสิ้นวัน", icon="📥"),
        st.Page("pages/purchase_history.py", title="ประวัติการซื้อ", icon="📋"),
        st.Page("pages/load_order.py", title="สั่งโหลด (จองคิว)", icon="🚚"),
        st.Page("pages/weigh_out.py", title="ชั่งออก (Weigh Out)", icon="⚖️"),
        st.Page("pages/truck_monitor_report.py", title="🎛️ ติดตามสถานะรถวิ่งงานสด", icon="🎯"),  # ผู้จัดการเห็นด้วยเพื่อคุมงาน
        st.Page("pages/destination_scan.py", title="สแกนหลักฐานปลายทาง", icon="📸"),
        st.Page("pages/sales_clearing.py", title="เคลียร์บิลปลายทาง", icon="💰"),
        st.Page("pages/stock_balance.py", title="สต็อกคงเหลือ", icon="📦"),
        st.Page("pages/truck_management.py", title="จัดการรถ/คนขับ", icon="🚘"),
        st.Page("pages/receipt_entry.py", title="บันทึกเงินโอน", icon="💵"),
        st.Page("pages/freight_payment.py", title="จ่ายค่าขนส่ง", icon="🚛"),
        st.Page("pages/manual_adjustment.py", title="ปรับยอดสต็อกด้วยมือ", icon="🔧"),
        st.Page("pages/dashboard.py", title="แดชบอร์ดผู้บริหาร", icon="📊"),
        st.Page("pages/report_sales.py", title="รายงานการขาย/กำไร/ภาษี", icon="📈"),
        st.Page("pages/report_freight.py", title="รายงานค่าขนส่ง/ค่าปรับ", icon="📉"),
        st.Page("pages/report_debtors.py", title="รายงานสถานะลูกหนี้-เจ้าหนี้", icon="📑"),
    ]

# 🧾 เคสที่ 3: สิทธิ์ของพนักงานเสมียนลาน (clerk)
elif role == "clerk":
    pages += [
        st.Page("pages/purchase_entry.py", title="บันทึกซื้อเข้าสิ้นวัน", icon="📥"),
        st.Page("pages/purchase_history.py", title="ประวัติการซื้อ", icon="📋"),
        st.Page("pages/load_order.py", title="สั่งโหลด (จองคิว)", icon="🚚"),
        st.Page("pages/weigh_out.py", title="ชั่งออก (Weigh Out)", icon="⚖️"),
        st.Page("pages/truck_monitor_report.py", title="🎛️ ติดตามสถานะรถวิ่งงานสด", icon="🎯"),  # เสมียนเห็นด้วยเพื่อเช็คคิวรถหน้าลาน
        st.Page("pages/destination_scan.py", title="สแกนหลักฐานปลายทาง", icon="📸"),
        st.Page("pages/sales_clearing.py", title="เคลียร์บิลปลายทาง", icon="💰"),
        st.Page("pages/stock_balance.py", title="สต็อกคงเหลือ", icon="📦"),
        st.Page("pages/truck_management.py", title="จัดการรถ/คนขับ", icon="🚘"),
        st.Page("pages/receipt_entry.py", title="บันทึกเงินโอน", icon="💵"),
        st.Page("pages/freight_payment.py", title="จ่ายค่าขนส่ง", icon="🚛"),
    ]

pg = st.navigation(pages)
pg.run()