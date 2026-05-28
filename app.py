import streamlit as st
import pandas as pd
from datetime import date, datetime
import time

# =====================================================
# 🔐 ตั้งค่า Supabase (เปลี่ยนเป็นของจริงเมื่อพร้อม)
# =====================================================
SUPABASE_URL = "https://xxxxxxxxxxxx.supabase.co"
SUPABASE_ANON_KEY = "your-anon-key-here"
# ถ้าต้องการใช้ Supabase จริง ให้ import และสร้าง client
# from supabase import create_client, Client
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# =====================================================
# 🎨 ธีมสว่าง (Light Mode) – ตั้งค่าผ่าน config.toml
#    หรือใส่ใน .streamlit/config.toml ของโปรเจกต์
#    [theme]
#    base="light"
# =====================================================

# =====================================================
# 🧩 Session State
# =====================================================
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "📥 บันทึกซื้อเข้าสิ้นวัน"

# =====================================================
# 🔑 หน้า Login (จำลอง)
# =====================================================
def login():
    st.title("🔐 เข้าสู่ระบบ - ลานเหล็กไทย")
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🧑‍💼 เจ้าของ", use_container_width=True):
            st.session_state.role = "owner"
            st.session_state.user = {"display_name": "เจ้าของ", "id": "000-owner"}
            st.rerun()
    with col2:
        if st.button("👨‍💼 ผู้จัดการ", use_container_width=True):
            st.session_state.role = "manager"
            st.session_state.user = {"display_name": "ผู้จัดการ", "id": "001-manager"}
            st.rerun()
    with col3:
        if st.button("🧾 เสมียน", use_container_width=True):
            st.session_state.role = "clerk"
            st.session_state.user = {"display_name": "เสมียน", "id": "002-clerk"}
            st.rerun()

# =====================================================
# 🧭 Sidebar
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

        menu_items = []
        if st.session_state.role in ["clerk", "manager", "owner"]:
            menu_items += [
                "📥 บันทึกซื้อเข้าสิ้นวัน",
                "📋 ประวัติการซื้อ",
                "🚚 สั่งโหลด (จองคิว)",
                "⚖️ ชั่งออก (Weigh Out)",
                "📸 สแกนหลักฐานปลายทาง",
                "💰 เคลียร์บิลปลายทาง"
            ]
        if st.session_state.role in ["clerk", "manager"]:
            menu_items += ["💵 บันทึกเงินโอน", "🚛 จ่ายค่าขนส่ง"]
        if st.session_state.role in ["clerk", "manager", "owner"]:
            menu_items += ["📦 สต็อกคงเหลือ"]
        if st.session_state.role in ["manager", "owner"]:
            menu_items += ["🔧 ปรับยอดสต็อกด้วยมือ"]
        if st.session_state.role in ["manager", "owner"]:
            menu_items += ["📊 แดชบอร์ด", "📈 รายงานการขาย/กำไร/ภาษี", "📉 รายงานค่าขนส่ง/ค่าปรับ", "📑 รายงานสถานะลูกหนี้-เจ้าหนี้"]
        if st.session_state.role == "owner":
            menu_items += ["⚙️ ตั้งค่าระบบ", "👥 จัดการผู้ใช้"]
        if st.session_state.role in ["clerk", "manager", "owner"]:
            menu_items += ["🚘 จัดการรถ/คนขับ"]

        for item in menu_items:
            if st.button(item, use_container_width=True):
                st.session_state.current_page = item
                st.rerun()

# =====================================================
# 📥 1. บันทึกซื้อเข้าสิ้นวัน (หลายเกรด / แยก Phys-Rep / ราคาแยก)
# =====================================================
def page_purchase_entry():
    st.header("📥 บันทึกซื้อเข้าสิ้นวัน (เพิ่มสต็อก Physical / Reporting แยกตามเกรด)")

    product_types = ["เหล็กเกรด A", "เหล็กเกรด B", "เศษเหล็กผสม"]  # TODO: ดึงจาก product_types

    with st.form("purchase_entry_form"):
        purchase_date = st.date_input("วันที่ซื้อ", date.today())
        st.markdown("---")

        if "purchase_rows" not in st.session_state:
            st.session_state.purchase_rows = []

        add_row = st.form_submit_button("➕ เพิ่มแถวสินค้า")
        if add_row:
            st.session_state.purchase_rows.append({
                "product": product_types[0],
                "physical_weight": 0,
                "physical_price": 0.0,
                "reporting_weight": 0,
                "reporting_price": 0.0
            })
            st.rerun()

        for i, row in enumerate(st.session_state.purchase_rows):
            cols = st.columns([2, 1.2, 1.2, 1.2, 1.2, 0.8])
            with cols[0]:
                row["product"] = st.selectbox("ประเภท", product_types, key=f"prod_{i}")
            with cols[1]:
                row["physical_weight"] = st.number_input("นน.Physical (kg)", min_value=0, step=100, key=f"pw_{i}", value=row["physical_weight"])
            with cols[2]:
                row["physical_price"] = st.number_input("ราคา/ตัน Phys", min_value=0.0, step=10.0, key=f"pp_{i}", value=row["physical_price"])
            with cols[3]:
                row["reporting_weight"] = st.number_input("นน.Reporting (kg)", min_value=0, step=100, key=f"rw_{i}", value=row["reporting_weight"])
            with cols[4]:
                row["reporting_price"] = st.number_input("ราคา/ตัน Rep", min_value=0.0, step=10.0, key=f"rp_{i}", value=row["reporting_price"])
            with cols[5]:
                if st.form_submit_button("🗑️", key=f"del_{i}"):
                    del st.session_state.purchase_rows[i]
                    st.rerun()

        st.markdown("---")

        preview_btn = st.form_submit_button("🔍 ตรวจสอบข้อมูล (Preview)")
        if preview_btn:
            if not st.session_state.purchase_rows:
                st.warning("กรุณาเพิ่มรายการสินค้าอย่างน้อย 1 รายการ")
            else:
                st.subheader("📋 ตัวอย่างข้อมูลก่อนบันทึก")
                total_phys_kg = sum(r["physical_weight"] for r in st.session_state.purchase_rows)
                total_rep_kg = sum(r["reporting_weight"] for r in st.session_state.purchase_rows)
                st.write(f"**วันที่ซื้อ:** {purchase_date}  |  **รายการ:** {len(st.session_state.purchase_rows)}")
                st.dataframe(
                    [{
                        "ประเภท": r["product"],
                        "Physical kg": r["physical_weight"],
                        "ราคา/ตัน": r["physical_price"],
                        "Reporting kg": r["reporting_weight"],
                        "ราคา/ตัน": r["reporting_price"]
                    } for r in st.session_state.purchase_rows]
                )
                st.info(f"รวม Physical: {total_phys_kg:,} กก.  |  Reporting: {total_rep_kg:,} กก.")
                st.warning("กรุณากด 'ยืนยันบันทึก' เพื่อบันทึกจริง")

        confirm_btn = st.form_submit_button("✅ ยืนยันบันทึกข้อมูล")
        if confirm_btn:
            if not st.session_state.purchase_rows:
                st.error("ไม่มีรายการสินค้า")
            else:
                # TODO: INSERT purchase_orders + purchase_lines + inventory_transactions
                st.success(f"บันทึกใบซื้อวันที่ {purchase_date} เรียบร้อย! (เพิ่มสต็อกทั้ง 2 ถัง)")
                st.balloons()
                st.session_state.purchase_rows = []
                st.rerun()

    if st.button("🖨️ พิมพ์สลิปสรุปการซื้อ"):
        st.write("พิมพ์สลิปแล้ว (จำลอง)")  # TODO: INSERT print_logs

# =====================================================
# 📋 2. ประวัติการซื้อ (ไม่มี Dashboard, เน้นน้ำหนัก)
# =====================================================
def page_purchase_history():
    st.header("📋 ประวัติการซื้อ")
    st.write("ค้นหาตามช่วงวันที่, ประเภทสินค้า")
    # TODO: ดึงข้อมูลจาก Supabase
    demo_data = [
        {"เลขที่บิล": "P0001", "วันที่": "2026-05-27", "รายการ": 2, "Physical kg": 1520, "Reporting kg": 1200},
        {"เลขที่บิล": "P0002", "วันที่": "2026-05-26", "รายการ": 1, "Physical kg": 800, "Reporting kg": 800}
    ]
    st.dataframe(demo_data, use_container_width=True)

    if st.button("ดูรายละเอียด"):
        st.write("แสดงรายละเอียดแต่ละบรรทัด (purchase_lines) ที่นี่")
    if st.button("🖨️ พิมพ์ซ้ำ"):
        st.write("พิมพ์เอกสารอีกครั้ง (reprint)")

# =====================================================
# 🚚 3. สั่งโหลด (เลือกรถ, ดึงคนขับ/บริษัท, เลือกสินค้า, ไม่เลือก freight mode)
# =====================================================
def page_load_order():
    st.header("🚚 สั่งโหลด (จองคิว)")
    # TODO: ดึงทะเบียนจาก trucks
    truck_plate = st.selectbox("ทะเบียนรถ", ["80-1234", "80-5678"])
    if truck_plate:
        # จำลองข้อมูลจากตาราง trucks (รวมบริษัทขนส่ง, วิธีคิดค่าขนส่ง – ดูจาก settings)
        st.write("👨‍✈️ คนขับ: สมชาย  |  📞 081-234-5678  |  🏢 บริษัท: สมชายขนส่ง")
    st.markdown("---")
    st.subheader("รายการสินค้าที่จะโหลด")
    col1, col2 = st.columns([2,1])
    with col1:
        product = st.selectbox("ประเภทสินค้า", ["เหล็กเกรด A", "เหล็กเกรด B"])
    with col2:
        est_weight = st.number_input("น้ำหนักโดยประมาณ (kg)", min_value=0, step=100)
    if st.button("เพิ่มรายการสินค้า"):
        st.session_state.setdefault("load_items", []).append({"product": product, "weight": est_weight})
    if "load_items" in st.session_state and st.session_state.load_items:
        st.write("สินค้าที่เลือก:")
        st.table(st.session_state.load_items)

    if st.button("Preview & บันทึก"):
        # TODO: บันทึก load_orders + load_items (ถ้ามีตารางลูก)
        st.success("จองคิวเรียบร้อย")
        st.balloons()
        st.session_state.load_items = []
        st.rerun()

# =====================================================
# ⚖️ 4. ชั่งออก (เลือก Load Order, Gross/Tare, Net คำนวณเอง, น้ำหนักปลายทาง, VAT)
# =====================================================
def page_weigh_out():
    st.header("⚖️ ชั่งออก (ตัดสต็อกหน้าลานทันที)")
    load_order = st.selectbox("เลือก Load Order", ["LO0001", "LO0002"])
    if load_order:
        st.write("รถ: 80-1234 | สินค้า: เหล็กเกรด A | ปลายทาง: โรงงาน A")
    col1, col2, col3 = st.columns(3)
    with col1:
        gross = st.number_input("น้ำหนักหนัก (Gross) kg", min_value=0, value=15000)
    with col2:
        tare = st.number_input("น้ำหนักเบา (Tare) kg", min_value=0, value=5000)
    with col3:
        net = gross - tare if gross >= tare else 0
        st.metric("น้ำหนักสุทธิ (Net)", f"{net:,} kg")
    dest_weight = st.number_input("น้ำหนักปลายทาง (kg) (ใส่เมื่อมีข้อมูล)", min_value=0, value=0)
    transit_loss = net - dest_weight if net >= dest_weight else 0
    if dest_weight > 0:
        st.write(f"🚚 Transit Loss: {transit_loss:,} kg")
    price_per_ton = st.number_input("ราคาขายต่อตัน (บาท)", min_value=0.0, value=8000.0)
    vat_mode = st.radio("ประเภท VAT", ["ปกติ (มี VAT)", "นอกระบบ (No VAT)"])

    if st.button("Preview & บันทึก"):
        # TODO: บันทึก weigh_out, ตัด PHYSICAL stock ทันที
        st.success("ชั่งออกเรียบร้อย ตัด Physical Stock แล้ว")
        st.write("🖨️ พิมพ์สลิป 80mm (มี QR)")
    if st.button("พิมพ์สลิป"):
        st.write("พิมพ์ซ้ำ")

# =====================================================
# 📸 5. สแกนหลักฐานปลายทาง (placeholder)
# =====================================================
def page_destination_scan():
    st.header("📸 สแกนหลักฐานปลายทาง (สำหรับคนขับ)")
    st.file_uploader("อัปโหลดรูปใบชั่ง", type=["jpg","png"])
    st.number_input("น้ำหนักชั่งปลายทาง (kg)", min_value=0)
    st.number_input("% สิ่งเจือปน", min_value=0.0, max_value=100.0, step=0.1)
    if st.button("ส่งข้อมูล"):
        st.success("อัปโหลดสำเร็จ")

# =====================================================
# 💰 6. เคลียร์บิลปลายทาง (Sales Clearing)
# =====================================================
def page_sales_clearing():
    st.header("💰 เคลียร์บิลปลายทาง (คำนวณเงิน, VAT/No VAT)")
    st.write("เลือก Weigh Out, คำนวณราคาจาก net billable, เลือกประเภทบิล")
    st.info("หน้านี้จะดึงข้อมูลจาก Weigh Out + Destination Weigh In มาคำนวณ (อยู่ในระหว่างพัฒนา)")

# =====================================================
# 💵 7. บันทึกเงินโอน
# =====================================================
def page_receipt_entry():
    st.header("💵 ตรวจสอบและบันทึกเงินโอน")
    st.write("แสดงรายการ Sales Clearing ที่ยังไม่ได้รับเงิน")

# =====================================================
# 🚛 8. จ่ายค่าขนส่ง
# =====================================================
def page_freight_payment():
    st.header("🚛 จ่ายค่าขนส่งให้สิบล้อ")
    st.write("คำนวณจาก Load Order + Transit Loss")

# =====================================================
# 📦 9. สต็อกคงเหลือ
# =====================================================
def page_stock_balance():
    st.header("📦 สต็อกคงเหลือ (Physical / Reporting)")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Physical", "1,250,000 kg")
    with col2:
        st.metric("Reporting", "980,000 kg")

# =====================================================
# 🔧 10. ปรับยอดสต็อกด้วยมือ
# =====================================================
def page_manual_adjustment():
    st.header("🔧 ปรับยอดสต็อกด้วยมือ (เฉพาะผู้จัดการ/เจ้าของ)")

# =====================================================
# 📊 11. แดชบอร์ด
# =====================================================
def page_dashboard():
    st.header("📊 แดชบอร์ดผู้บริหาร")
    st.line_chart([10,20,15,30])

# =====================================================
# 📈 12. รายงานการขาย/กำไร/ภาษี
# =====================================================
def page_report_sales():
    st.header("📈 รายงานการขาย/กำไร/ภาษี")

# =====================================================
# 📉 13. รายงานค่าขนส่ง/ค่าปรับ
# =====================================================
def page_report_freight():
    st.header("📉 รายงานค่าขนส่ง/ค่าปรับ")

# =====================================================
# 📑 14. รายงานลูกหนี้/เจ้าหนี้
# =====================================================
def page_report_debtors():
    st.header("📑 รายงานลูกหนี้/เจ้าหนี้")

# =====================================================
# ⚙️ 15. ตั้งค่าระบบ
# =====================================================
def page_settings():
    st.header("⚙️ ตั้งค่าระบบ")
    st.number_input("เกณฑ์ % น้ำหนักขาด", value=0.5)
    st.number_input("เกณฑ์ กก. ขาด", value=50)
    st.number_input("อัตราค่าขนส่งเหมาเที่ยว (บาท)", value=3000.0)
    st.number_input("อัตราค่าขนส่งต่อตัน (บาท)", value=100.0)
    st.radio("ฐานน้ำหนักเริ่มต้นสำหรับ PER_TON", ["ต้นทาง", "ปลายทาง"], index=0)

# =====================================================
# 👥 16. จัดการผู้ใช้
# =====================================================
def page_user_management():
    st.header("👥 จัดการผู้ใช้ (เจ้าของเท่านั้น)")

# =====================================================
# 🚘 17. จัดการรถ/คนขับ (เพิ่มบริษัทขนส่ง, วิธีคิดค่าขนส่ง)
# =====================================================
def page_truck_management():
    st.header("🚘 จัดการรถ/คนขับ")
    with st.form("truck_form"):
        plate = st.text_input("ทะเบียนรถ")
        driver = st.text_input("ชื่อคนขับ")
        phone = st.text_input("เบอร์โทร")
        company = st.text_input("บริษัทขนส่ง")
        empty_weight = st.number_input("น้ำหนักเบา (kg)", min_value=0)
        freight_method = st.radio("วิธีคิดค่าขนส่งเริ่มต้น", ["เหมาเที่ยว", "บาทต่อตัน"])
        if st.form_submit_button("บันทึก"):
            st.success("บันทึกข้อมูลรถเรียบร้อย")
            # TODO: INSERT/UPDATE trucks

# =====================================================
# 🎯 Main App
# =====================================================
def main():
    st.set_page_config(page_title="ลานเหล็กไทย", page_icon="🏗️", layout="wide")

    if not st.session_state.user:
        login()
        return

    sidebar()
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
