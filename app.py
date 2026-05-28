import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import date, datetime
import time

# =====================================================
# 🔐 ตั้งค่า Supabase (ต้องเปลี่ยนเป็นของจริง)
# =====================================================
SUPABASE_URL = "https://pknucflvhkwcecrylzfh.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBrbnVjZmx2aGt3Y2VjcnlsemZoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk4NDc3MTAsImV4cCI6MjA5NTQyMzcxMH0.Jd2Hlaxw6YGvYi3J6fKvocA-hjJGj1Ygs2tV1ektAhY"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# =====================================================
# 🧩 Session State สำหรับจำลองการ Login
# =====================================================
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None

# =====================================================
# 🔑 หน้า Login (จำลองด้วยการเลือก Role)
# =====================================================
def login():
    st.title("🔐 เข้าสู่ระบบ - ลานเหล็กไทย")
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🧑‍💼 เข้าใช้งานในฐานะ เจ้าของ", use_container_width=True):
            st.session_state.role = "owner"
            st.session_state.user = {"display_name": "เจ้าของ", "id": "000-owner"}
            st.rerun()
    with col2:
        if st.button("👨‍💼 เข้าใช้งานในฐานะ ผู้จัดการ", use_container_width=True):
            st.session_state.role = "manager"
            st.session_state.user = {"display_name": "ผู้จัดการ", "id": "001-manager"}
            st.rerun()
    with col3:
        if st.button("🧾 เข้าใช้งานในฐานะ เสมียน", use_container_width=True):
            st.session_state.role = "clerk"
            st.session_state.user = {"display_name": "เสมียน", "id": "002-clerk"}
            st.rerun()

# =====================================================
# 🧭 Sidebar & ระบบนำทาง
# =====================================================
def sidebar():
    with st.sidebar:
        st.title("🏭 ลานเหล็กไทย")
        st.markdown(f"👤 {st.session_state.user['display_name']} ({st.session_state.role})")

        if st.button("ออกจากระบบ"):
            st.session_state.user = None
            st.session_state.role = None
            st.rerun()

        st.markdown("---")

        # สร้างรายการเมนูตาม Role
        menu_items = []

        if st.session_state.role in ["clerk", "manager", "owner"]:
            menu_items += ["📥 บันทึกซื้อเข้าสิ้นวัน", "📋 ประวัติการซื้อ"]
            menu_items += ["🚚 สั่งโหลด (จองคิว)", "⚖️ ชั่งออก (Weigh Out)"]
            menu_items += ["📸 สแกนหลักฐานปลายทาง", "💰 เคลียร์บิลปลายทาง"]
        if st.session_state.role in ["clerk", "manager"]:
            menu_items += ["💵 บันทึกเงินโอน", "🚛 จ่ายค่าขนส่ง"]
        if st.session_state.role in ["clerk", "manager", "owner"]:
            menu_items += ["📦 สต็อกคงเหลือ"]
        if st.session_state.role in ["manager", "owner"]:
            menu_items += ["🔧 ปรับยอดสต็อกด้วยมือ"]
        if st.session_state.role in ["manager", "owner"]:
            menu_items += ["📊 แดชบอร์ด"]
            menu_items += ["📈 รายงานการขาย/กำไร/ภาษี"]
            menu_items += ["📉 รายงานค่าขนส่ง/ค่าปรับ"]
            menu_items += ["📑 รายงานสถานะลูกหนี้-เจ้าหนี้"]
        if st.session_state.role == "owner":
            menu_items += ["⚙️ ตั้งค่าระบบ", "👥 จัดการผู้ใช้"]
        if st.session_state.role in ["clerk", "manager", "owner"]:
            menu_items += ["🚘 จัดการรถ/คนขับ"]

        # ปุ่มเมนู
        selected = None
        for item in menu_items:
            if st.button(item, use_container_width=True):
                selected = item
                st.session_state.current_page = item
                st.rerun()

        return selected

# =====================================================
# 📦 หน้าย่อยต่าง ๆ (ฟังก์ชันเปล่า ๆ พร้อมโครง)
# =====================================================
def page_purchase_entry():
    st.header("📥 บันทึกซื้อเข้าสิ้นวัน (เพิ่มสต็อกทั้ง 2 ถัง)")
    with st.form("purchase_form"):
        col1, col2 = st.columns(2)
        with col1:
            purchase_date = st.date_input("วันที่ซื้อ", date.today())
            physical_weight = st.number_input("น้ำหนัก Physical (กก.)", min_value=0, step=100)
            reporting_weight = st.number_input("น้ำหนัก Reporting (กก.)", min_value=0, step=100)
        with col2:
            price_per_ton = st.number_input("ราคาต่อตัน (บาท)", min_value=0.0, step=10.0)
            st.markdown("#### Preview (จะคำนวณเมื่อกดปุ่ม)")
            if st.form_submit_button("ตรวจสอบข้อมูล"):
                st.info(f"รวม Physical {physical_weight:,} กก. | Reporting {reporting_weight:,} กก. | มูลค่ารวม {(physical_weight/1000)*price_per_ton:,.2f} บาท")
            submitted = st.form_submit_button("ยืนยันบันทึก")
            if submitted:
                # TODO: insert to purchases + inventory_transactions
                st.success("บันทึกเรียบร้อย! (โค้ดจริงใส่ Supabase ที่นี่)")
                # ตัวอย่าง: supabase.table("purchases").insert({...}).execute()
                st.balloons()

    if st.button("พิมพ์สลิปสรุป"):
        st.write("🖨️ จำลองพิมพ์สลิป (A5/80mm) [ภายหลังเรียก print_log]")

def page_purchase_history():
    st.header("📋 ประวัติการซื้อ")
    st.write("แสดงตาราง purchases ทั้งหมด")
    # ตัวอย่างดึงข้อมูลจริง
    # response = supabase.table("purchases").select("*").execute()
    # st.dataframe(response.data)
    st.dataframe(pd.DataFrame(columns=["วันที่","Physical","Reporting","ราคา","ผู้บันทึก"]))
    if st.button("พิมพ์ซ้ำ"):
        st.write("📄 พิมพ์ซ้ำเอกสารที่เลือก")

def page_load_order():
    st.header("🚚 สั่งโหลด (จองคิว)")
    # เลือกรถ
    st.selectbox("ทะเบียนรถ", ["80-1234", "80-5678"], key="truck_plate")
    st.radio("รูปแบบค่าขนส่ง", ["เหมาเที่ยว", "บาทต่อตัน"], key="freight_mode")
    if st.session_state.freight_mode == "บาทต่อตัน":
        st.radio("ฐานน้ำหนัก", ["ต้นทาง", "ปลายทาง"], key="weight_base")
        st.number_input("อัตราค่าขนส่ง (บาท/ตัน)", min_value=0.0, value=100.0)
    else:
        st.number_input("ค่าขนส่งเหมา (บาท)", min_value=0.0, value=3000.0)
    if st.button("Preview & บันทึก"):
        st.success("สั่งโหลดเรียบร้อย!")
        st.balloons()

def page_weigh_out():
    st.header("⚖️ ชั่งออก (ตัดสต็อกหน้าลานทันที)")
    st.text_input("เลขที่ Load Order")
    col1, col2 = st.columns(2)
    with col1:
        gross = st.number_input("น้ำหนักรวม (kg)", min_value=0)
    with col2:
        tare = st.number_input("น้ำหนักรถ (kg)", min_value=0)
    net = gross - tare if gross >= tare else 0
    st.metric("น้ำหนักสุทธิ", f"{net:,} kg")
    st.radio("ประเภท VAT", ["ปกติ (มี VAT)", "นอกระบบ (No VAT)"])
    if st.button("ยืนยันและพิมพ์สลิป"):
        st.success("ตัดสต็อก Physical เรียบร้อย!")
        st.write("🖨️ พิมพ์สลิป 80mm (QR)")

def page_destination_scan():
    st.header("📸 สแกนหลักฐานปลายทาง (สำหรับคนขับ)")
    st.file_uploader("อัปโหลดรูปใบชั่งปลายทาง", type=["jpg","png"])
    st.number_input("น้ำหนักชั่งปลายทาง (kg)", min_value=0)
    st.number_input("% สิ่งเจือปน", min_value=0.0, max_value=100.0, step=0.1)
    if st.button("ส่งข้อมูล"):
        st.success("อัปโหลดสำเร็จ!")

def page_sales_clearing():
    st.header("💰 เคลียร์บิลปลายทาง (คำนวณเงิน, เลือก VAT/No VAT)")
    st.selectbox("เลือก Weigh Out", [])  # ดึงจาก DB
    st.number_input("ราคาขายต่อตัน (บาท)", min_value=0.0)
    st.selectbox("ประเภทบิล", ["ปกติ (มี VAT)", "นอกระบบ (No VAT)"])
    if st.button("คำนวณ Preview"):
        st.write("Transit Loss: ... | เงินรวม: ... | VAT: ...")
    if st.button("ยืนยันเคลียร์บิล"):
        st.success("เคลียร์บิลเรียบร้อย!")

def page_receipt_entry():
    st.header("💵 ตรวจสอบและบันทึกเงินโอน")
    st.write("รายการที่รอรับเงิน:")
    # ตารางตัวอย่าง
    df = pd.DataFrame({"บิล": [1,2], "ยอด": [50000, 70000], "สถานะ": ["ยังไม่รับ","ยังไม่รับ"]})
    st.dataframe(df)
    if st.button("บันทึกการรับเงิน (Preview)"):
        st.success("รับเงินเรียบร้อย!")

def page_freight_payment():
    st.header("🚛 จ่ายค่าขนส่งให้สิบล้อ")
    st.write("คำนวณจาก Load Order + Transit Loss")
    st.metric("ค่าขนส่งสุทธิ", "2,850 บาท (หักค่าปรับ 150)")
    if st.button("ยืนยันการจ่าย"):
        st.success("บันทึกการจ่ายเรียบร้อย!")

def page_stock_balance():
    st.header("📦 สต็อกคงเหลือ (Physical / Reporting)")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Physical Stock", "1,250,000 kg")
    with col2:
        st.metric("Reporting Stock", "980,000 kg")
    st.info("จะแสดงกราฟและ FIFO layers ในขั้นตอนต่อไป")

def page_manual_adjustment():
    st.header("🔧 ปรับยอดสต็อกด้วยมือ")
    st.radio("ประเภทสต็อก", ["Physical", "Reporting"])
    st.number_input("จำนวนที่ปรับ (+/-) kg", value=0, step=100)
    st.text_area("เหตุผล")
    if st.button("Preview & ยืนยัน"):
        st.warning("การปรับยอดนี้จะถูกบันทึกถาวร")

def page_dashboard():
    st.header("📊 แดชบอร์ดผู้บริหาร")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("กำไรวันนี้", "35,000 บาท")
    with col2:
        st.metric("เที่ยวรถวันนี้", 8)
    with col3:
        st.metric("สต็อกคงเหลือ", "1.2 ล้าน กก.")
    st.line_chart([1,2,3,4])

def page_report_sales():
    st.header("📈 รายงานการขาย/กำไร/ภาษี")
    st.date_input("เลือกช่วงวันที่")
    st.write("ตารางแยกตาม VAT/No VAT")
    st.dataframe(pd.DataFrame({"ประเภท":["ปกติ","นอกระบบ"],"ยอดขาย":[120000,50000]}))

def page_report_freight():
    st.header("📉 รายงานค่าขนส่ง/ค่าปรับ")
    st.dataframe(pd.DataFrame(columns=["ทะเบียน","ค่าขนส่ง","ค่าปรับ","สุทธิ"]))

def page_report_debtors():
    st.header("📑 รายงานลูกหนี้/เจ้าหนี้")
    st.write("โรงงานที่ยังค้างเงิน และค่ารถที่ยังไม่จ่าย")
    st.dataframe(pd.DataFrame(columns=["รายการ","ยอดเงิน","สถานะ"]))

def page_settings():
    st.header("⚙️ ตั้งค่าระบบ")
    st.number_input("เกณฑ์ % น้ำหนักขาดที่ยอมรับได้", value=0.5)
    st.number_input("เกณฑ์ กก. ที่ยอมรับได้", value=50)
    if st.button("บันทึกการตั้งค่า"):
        st.success("บันทึกแล้ว")

def page_user_management():
    st.header("👥 จัดการผู้ใช้")
    st.write("(จะเชื่อมกับ Supabase Auth)")
    st.text_input("Email ผู้ใช้ใหม่")
    st.selectbox("Role", ["clerk","manager","owner"])
    if st.button("เพิ่มผู้ใช้"):
        st.success("เพิ่มผู้ใช้เรียบร้อย")

def page_truck_management():
    st.header("🚘 จัดการรถ/คนขับ")
    st.text_input("ทะเบียนรถ")
    st.text_input("ชื่อคนขับ")
    st.number_input("น้ำหนักเบา (kg)")
    if st.button("บันทึก"):
        st.success("บันทึกข้อมูลรถเรียบร้อย")

# =====================================================
# 🎯 Main App
# =====================================================
def main():
    st.set_page_config(page_title="ลานเหล็กไทย", page_icon="🏗️", layout="wide")

    if not st.session_state.user:
        login()
        return

    # ถ้า login แล้ว
    selected_page = sidebar()

    # ใช้ session_state เพื่อจำหน้า
    if "current_page" not in st.session_state:
        st.session_state.current_page = "📊 แดชบอร์ด"  # default สำหรับ manager/owner; อาจจะเปลี่ยนตาม role

    # แสดงหน้าตามที่เลือก
    page = st.session_state.current_page
    if page == "📥 บันทึกซื้อเข้าสิ้นวัน":
        page_purchase_entry()
    elif page == "📋 ประวัติการซื้อ":
        page_purchase_history()
    elif page == "🚚 สั่งโหลด (จองคิว)":
        page_load_order()
    elif page == "⚖️ ชั่งออก (Weigh Out)":
        page_weigh_out()
    elif page == "📸 สแกนหลักฐานปลายทาง":
        page_destination_scan()
    elif page == "💰 เคลียร์บิลปลายทาง":
        page_sales_clearing()
    elif page == "💵 บันทึกเงินโอน":
        page_receipt_entry()
    elif page == "🚛 จ่ายค่าขนส่ง":
        page_freight_payment()
    elif page == "📦 สต็อกคงเหลือ":
        page_stock_balance()
    elif page == "🔧 ปรับยอดสต็อกด้วยมือ":
        page_manual_adjustment()
    elif page == "📊 แดชบอร์ด":
        page_dashboard()
    elif page == "📈 รายงานการขาย/กำไร/ภาษี":
        page_report_sales()
    elif page == "📉 รายงานค่าขนส่ง/ค่าปรับ":
        page_report_freight()
    elif page == "📑 รายงานสถานะลูกหนี้-เจ้าหนี้":
        page_report_debtors()
    elif page == "⚙️ ตั้งค่าระบบ":
        page_settings()
    elif page == "👥 จัดการผู้ใช้":
        page_user_management()
    elif page == "🚘 จัดการรถ/คนขับ":
        page_truck_management()
    else:
        st.error("ไม่พบหน้าที่เลือก")

if __name__ == "__main__":
    main()
