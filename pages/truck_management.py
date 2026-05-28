import streamlit as st
import pandas as pd

st.header("🚘 จัดการรถ/คนขับ (เพิ่ม / แก้ไข ข้อมูลรถ)")

# ---- ข้อมูลรถ (ถ้ายังไม่มีใน session_state) ----
if "trucks_list" not in st.session_state:
    st.session_state.trucks_list = [
        {
            "plate": "80-1234",
            "driver": "สมชาย",
            "phone": "081-234-5678",
            "company": "สมชายขนส่ง",
            "empty_weight": 5500,
            "freight_method": "เหมาเที่ยว",
            "freight_rate": 3000.0   # ราคาที่ตั้งไว้
        },
        {
            "plate": "80-5678",
            "driver": "สมศักดิ์",
            "phone": "089-876-5432",
            "company": "ศักดิ์ขนส่ง",
            "empty_weight": 5800,
            "freight_method": "บาทต่อตัน",
            "freight_rate": 100.0
        }
    ]

# ---- แสดงตารางรถปัจจุบัน ----
st.subheader("รายการรถที่มีอยู่")
df = pd.DataFrame([
    {
        "ทะเบียน": t["plate"],
        "คนขับ": t["driver"],
        "เบอร์": t["phone"],
        "บริษัท": t["company"],
        "น้ำหนักเบา (kg)": t["empty_weight"],
        "วิธีคิดค่าขนส่ง": t["freight_method"],
        "อัตรา": f"{t['freight_rate']:,.2f}"
    } for t in st.session_state.trucks_list
])
st.dataframe(df, use_container_width=True, hide_index=True)

# ---- ฟอร์มเพิ่ม / แก้ไขรถ ----
st.markdown("---")
st.subheader("➕ เพิ่ม / แก้ไข ข้อมูลรถ")

with st.form("truck_form"):
    # เลือกว่าจะเพิ่มใหม่หรือแก้ไข
    truck_plates = [""] + [t["plate"] for t in st.session_state.trucks_list]
    selected_plate = st.selectbox(
        "เลือกทะเบียนรถ (ปล่อยว่างเพื่อเพิ่มใหม่)",
        truck_plates,
        index=0
    )

    # ถ้าเลือกของเดิมให้ดึงข้อมูลมาแสดง
    if selected_plate:
        existing_truck = next(t for t in st.session_state.trucks_list if t["plate"] == selected_plate)
        # ถ้ามีข้อมูลเก่าใช้เป็นค่าเริ่มต้น
        init_plate = existing_truck["plate"]
        init_driver = existing_truck["driver"]
        init_phone = existing_truck["phone"]
        init_company = existing_truck["company"]
        init_empty_weight = existing_truck["empty_weight"]
        init_method = existing_truck["freight_method"]
        init_rate = existing_truck["freight_rate"]
    else:
        init_plate = ""
        init_driver = ""
        init_phone = ""
        init_company = ""
        init_empty_weight = 0
        init_method = "เหมาเที่ยว"
        init_rate = 0.0

    plate = st.text_input("ทะเบียนรถ *", value=init_plate)
    col1, col2 = st.columns(2)
    with col1:
        driver = st.text_input("ชื่อคนขับ *", value=init_driver)
        phone = st.text_input("เบอร์โทร", value=init_phone)
    with col2:
        company = st.text_input("บริษัทขนส่ง", value=init_company)
        empty_weight = st.number_input("น้ำหนักเบา (kg)", min_value=0, value=init_empty_weight)

    # เลือกวิธีคิดค่าขนส่ง
    freight_method = st.radio(
        "วิธีคิดค่าขนส่งเริ่มต้น *",
        ["เหมาเที่ยว", "บาทต่อตัน"],
        index=0 if init_method == "เหมาเที่ยว" else 1
    )

    # ช่องกรอกอัตราค่าขนส่ง ตามวิธีที่เลือก
    if freight_method == "เหมาเที่ยว":
        freight_rate = st.number_input(
            "อัตราค่าขนส่ง (บาท/เที่ยว)",
            min_value=0.0, step=100.0,
            value=init_rate
        )
    else:
        freight_rate = st.number_input(
            "อัตราค่าขนส่ง (บาท/ตัน)",
            min_value=0.0, step=10.0,
            value=init_rate
        )

    submitted = st.form_submit_button("💾 บันทึกข้อมูลรถ")

    if submitted:
        # ตรวจสอบข้อมูลจำเป็น
        if not plate or not driver:
            st.error("กรุณากรอกทะเบียนรถและชื่อคนขับ")
        else:
            new_truck = {
                "plate": plate,
                "driver": driver,
                "phone": phone,
                "company": company,
                "empty_weight": empty_weight,
                "freight_method": freight_method,
                "freight_rate": freight_rate
            }
            if selected_plate:
                # แก้ไขรถเดิม
                for i, t in enumerate(st.session_state.trucks_list):
                    if t["plate"] == selected_plate:
                        st.session_state.trucks_list[i] = new_truck
                        break
                st.success(f"อัปเดตข้อมูลรถ {plate} เรียบร้อย!")
            else:
                # เพิ่มรถใหม่ (ตรวจสอบทะเบียนซ้ำ)
                if any(t["plate"] == plate for t in st.session_state.trucks_list):
                    st.error("ทะเบียนนี้มีอยู่แล้ว กรุณาเลือกแก้ไขแทน")
                else:
                    st.session_state.trucks_list.append(new_truck)
                    st.success(f"เพิ่มรถ {plate} เรียบร้อย!")
            st.balloons()
            st.rerun()

# ---- ปุ่มลบรถ ----
st.markdown("---")
if st.session_state.trucks_list:
    delete_plate = st.selectbox(
        "เลือกทะเบียนที่ต้องการลบ",
        [t["plate"] for t in st.session_state.trucks_list]
    )
    if st.button("🗑️ ลบรถคันนี้"):
        st.session_state.trucks_list = [
            t for t in st.session_state.trucks_list if t["plate"] != delete_plate
        ]
        st.success(f"ลบรถ {delete_plate} แล้ว")
        st.rerun()