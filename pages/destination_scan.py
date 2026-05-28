import streamlit as st

st.header("📸 สแกนหลักฐานปลายทาง (สำหรับคนขับ)")

st.write("อัปโหลดรูปใบชั่งน้ำหนักปลายทาง พร้อมข้อมูลน้ำหนักและสิ่งเจือปน")

uploaded_file = st.file_uploader("📷 เลือกรูปใบชั่งปลายทาง", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="ตัวอย่างรูปที่อัปโหลด", use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    received_weight = st.number_input("น้ำหนักชั่งปลายทาง (kg)", min_value=0, step=10)
with col2:
    impurity_pct = st.number_input("% สิ่งเจือปน", min_value=0.0, max_value=100.0, step=0.1, value=0.0)

# คำนวณน้ำหนักสุทธิหลังหักสิ่งเจือปน
net_billable = received_weight * (1 - impurity_pct / 100) if received_weight > 0 else 0
st.metric("น้ำหนักสุทธิที่คิดเงิน (โดยประมาณ)", f"{net_billable:,.2f} kg")

if st.button("📤 ส่งข้อมูล"):
    if uploaded_file is None:
        st.error("กรุณาอัปโหลดรูปใบชั่ง")
    elif received_weight <= 0:
        st.error("กรุณากรอกน้ำหนักปลายทางมากกว่า 0")
    else:
        # TODO: อัปโหลดรูปไป Supabase Storage, บันทึกข้อมูลลง destination_weigh_in
        st.success("อัปโหลดหลักฐานเรียบร้อย! เสมียนจะดำเนินการต่อในระบบ")