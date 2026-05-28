import streamlit as st
import pandas as pd

# =====================================================
# 🚛 ข้อมูลรถตัวอย่าง (ภายหลังดึงจาก Supabase)
# =====================================================
if "trucks_list" not in st.session_state:
    st.session_state.trucks_list = [
        {
            "plate": "80-1234",
            "driver": "สมชาย",
            "phone": "081-234-5678",
            "company": "สมชายขนส่ง",
            "empty_weight": 5500,
            "freight_method": "เหมาเที่ยว"
        },
        {
            "plate": "80-5678",
            "driver": "สมศักดิ์",
            "phone": "089-876-5432",
            "company": "ศักดิ์ขนส่ง",
            "empty_weight": 5800,
            "freight_method": "บาทต่อตัน"
        },
        {
            "plate": "80-9999",
            "driver": "สมบัติ",
            "phone": "082-111-2222",
            "company": "บัติโลจิสติกส์",
            "empty_weight": 6000,
            "freight_method": "เหมาเที่ยว"
        }
    ]

# =====================================================
# 🚚 หน้าสั่งโหลด
# =====================================================
st.header("🚚 สั่งโหลด (จองคิว)")

# ---- ค้นหารถ ----
st.subheader("🔍 ค้นหารถ (ทะเบียน / บริษัท / คนขับ)")
search_term = st.text_input("พิมพ์คำค้นหา (เช่น ทะเบียน, ชื่อบริษัท, ชื่อคนขับ)", value="")

# กรองข้อมูล
filtered_trucks = []
if search_term:
    term = search_term.lower()
    filtered_trucks = [
        t for t in st.session_state.trucks_list
        if term in t["plate"].lower() or term in t["company"].lower() or term in t["driver"].lower()
    ]
else:
    filtered_trucks = st.session_state.trucks_list  # แสดงทั้งหมดถ้าไม่มีคำค้นหา

if not filtered_trucks:
    st.warning("ไม่พบรถที่ตรงกับคำค้นหา")
    selected_truck = None
else:
    # แสดงตัวเลือก (ใช้ radio button ให้เห็นทีละคัน)
    option_label = [f"{t['plate']} | {t['company']} | {t['driver']}" for t in filtered_trucks]
    selected_label = st.radio("เลือกคันที่ต้องการ", option_label)
    selected_index = option_label.index(selected_label)
    selected_truck = filtered_trucks[selected_index]

# ---- แสดงข้อมูลรถที่เลือก ----
if selected_truck:
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("ทะเบียนรถ", selected_truck["plate"])
    col2.metric("คนขับ", selected_truck["driver"])
    col3.metric("เบอร์โทร", selected_truck["phone"])
    st.write(f"**บริษัทขนส่ง:** {selected_truck['company']}")
    st.write(f"**น้ำหนักรถเปล่า (Empty Wt.):** {selected_truck['empty_weight']} kg")
    st.write(f"**วิธีคิดค่าขนส่งเริ่มต้น:** {selected_truck['freight_method']} (ตามตั้งค่าระบบ)")
    # ในการใช้งานจริง freight mode/rate จะถูกดึงจาก settings อีกที

    # ---- รายการสินค้าที่จะโหลด ----
    st.markdown("---")
    st.subheader("📦 สินค้าที่จะโหลดในเที่ยวนี้")

    if "load_items" not in st.session_state:
        st.session_state.load_items = []

    col_prod, col_wt, col_btn = st.columns([2, 1, 1])
    with col_prod:
        product = st.selectbox("ประเภทสินค้า", ["เหล็กเกรด A", "เหล็กเกรด B", "เศษเหล็กผสม"])
    with col_wt:
        est_weight = st.number_input("น้ำหนักโดยประมาณ (kg)", min_value=0, step=100, value=0)
    with col_btn:
        if st.button("➕ เพิ่ม"):
            st.session_state.load_items.append({"product": product, "weight": est_weight})
            st.rerun()

    if st.session_state.load_items:
        st.write("**สินค้าที่เลือก:**")
        st.table(st.session_state.load_items)
        if st.button("🗑️ ล้างรายการสินค้า"):
            st.session_state.load_items = []
            st.rerun()

    # ---- บันทึก ----
    if st.button("✅ บันทึก Load Order"):
        # TODO: บันทึกลง load_orders + load_items (ตารางลูก) ใน Supabase
        # ส่งค่าต่างๆ เช่น truck_id, freight_mode จาก settings, รายการสินค้า
        st.success(f"บันทึกการจองคิวรถ {selected_truck['plate']} เรียบร้อย!")
        st.balloons()
        st.session_state.load_items = []
        # ในที่นี้เรายังไม่เคลียร์ selected_truck เพราะไม่ใช่ state
        st.rerun()

else:
    st.info("กรุณาเลือกหรือค้นหารถก่อน")