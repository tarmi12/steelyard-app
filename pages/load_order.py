import streamlit as st

st.header("🚚 สั่งโหลด (จองคิว)")

# จำลองข้อมูลรถ (ภายหลังดึงจาก trucks)
truck_options = {
    "80-1234": {"driver": "สมชาย", "phone": "081-234-5678", "company": "สมชายขนส่ง"},
    "80-5678": {"driver": "สมหญิง", "phone": "089-876-5432", "company": "สมหญิงโลจิสติกส์"},
}

truck_plate = st.selectbox("ทะเบียนรถ", list(truck_options.keys()))
if truck_plate:
    info = truck_options[truck_plate]
    st.write(f"👨‍✈️ คนขับ: {info['driver']}  |  📞 {info['phone']}  |  🏢 บริษัท: {info['company']}")

st.markdown("---")
st.subheader("รายการสินค้าที่จะโหลด")

# ใช้ session state เก็บรายการสินค้า (ชั่วคราว)
if "load_items" not in st.session_state:
    st.session_state.load_items = []

col1, col2 = st.columns([2, 1])
with col1:
    product = st.selectbox("ประเภทสินค้า", ["เหล็กเกรด A", "เหล็กเกรด B"])
with col2:
    est_weight = st.number_input("น้ำหนักโดยประมาณ (kg)", min_value=0, step=100, value=0)

if st.button("เพิ่มรายการสินค้า"):
    if est_weight > 0:
        st.session_state.load_items.append({
            "product": product,
            "weight": est_weight
        })
        st.success(f"เพิ่ม {product} {est_weight} kg")
    else:
        st.warning("กรุณาใส่น้ำหนักมากกว่า 0")

if st.session_state.load_items:
    st.write("**สินค้าที่เลือก:**")
    for idx, item in enumerate(st.session_state.load_items):
        cols = st.columns([2, 1, 0.8])
        cols[0].write(item["product"])
        cols[1].write(f"{item['weight']} kg")
        if cols[2].button("ลบ", key=f"del_load_{idx}"):
            del st.session_state.load_items[idx]
            st.rerun()

st.markdown("---")
if st.button("✅ ยืนยันการสั่งโหลด"):
    if not st.session_state.load_items:
        st.error("กรุณาเพิ่มรายการสินค้าอย่างน้อย 1 รายการ")
    else:
        # TODO: บันทึก load_orders + load_lines (ถ้ามี) ลง Supabase
        st.success("บันทึกการสั่งโหลดเรียบร้อย! (รหัส LO0001)")
        st.session_state.load_items = []
        st.rerun()