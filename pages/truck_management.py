import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.header("🚘 จัดการข้อมูลรถและคนขับ (ระบบใช้งานจริง)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ---- 1. ดึงข้อมูลรถทั้งหมดจากตาราง trucks จริง ----
try:
    truck_res = supabase.table("trucks").select("*").order("plate").execute()
    trucks_list = truck_res.data
except Exception as e:
    st.error(f"ไม่สามารถดึงข้อมูลรถได้: {e}")
    trucks_list = []

# ---- 2. แสดงตารางรถปัจจุบัน ----
st.subheader("📋 รายการรถในระบบปัจจุบัน")
if not trucks_list:
    st.info("ยังไม่มีข้อมูลรถในระบบ กรุณาเพิ่มข้อมูลด้านลาก")
else:
    df = pd.DataFrame([{
        "ID": t["id"],
        "ทะเบียน": t["plate"],
        "คนขับ": t["driver_name"],
        "เบอร์โทร": t["driver_phone"],
        "บริษัทขนส่ง": t["company"],
        "น้ำหนักเบา (kg)": t["empty_weight"],
        "วิธีคิดค่าขนส่ง": "เหมาเที่ยว" if t["freight_method"] == "FLAT_RATE" else "ต่อตัน",
        "อัตราเริ่มต้น": f"{float(t['freight_rate']):,.2f}"
    } for t in trucks_list])
    st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("---")

# ---- 3. ฟอร์ม เพิ่ม / แก้ไข ข้อมูลรถ ----
st.subheader("➕ เพิ่ม / แก้ไข ข้อมูลรถ")
with st.form("real_truck_form"):
    truck_plates = [""] + [t["plate"] for t in trucks_list]
    selected_plate = st.selectbox("เลือกทะเบียนรถเพื่อแก้ไข (หากต้องการเพิ่มใหม่ให้ปล่อยว่าง)", truck_plates)

    # ตั้งค่าตั้งต้นกรณีเลือกแก้ไข
    if selected_plate:
        existing = next(t for t in trucks_list if t["plate"] == selected_plate)
        init_plate = existing["plate"]
        init_driver = existing["driver_name"]
        init_phone = existing["driver_phone"] or ""
        init_company = existing["company"] or ""
        init_empty = existing["empty_weight"] or 0
        init_method = existing["freight_method"]
        init_rate = float(existing["freight_rate"])
    else:
        init_plate, init_driver, init_phone, init_company, init_empty, init_method, init_rate = "", "", "", "", 0, "FLAT_RATE", 0.0

    plate = st.text_input("ทะเบียนรถ *", value=init_plate)
    col1, col2 = st.columns(2)
    with col1:
        driver = st.text_input("ชื่อคนขับ *", value=init_driver)
        phone = st.text_input("เบอร์โทรคนขับ", value=init_phone)
    with col2:
        company = st.text_input("บริษัทขนส่ง/สังกัด", value=init_company)
        empty_weight = st.number_input("น้ำหนักรถเปล่าเริ่มต้น (kg)", min_value=0, value=init_empty, step=10)

    freight_method = st.radio("วิธีคิดค่าขนส่งเริ่มต้น", ["FLAT_RATE", "PER_TON"], 
                              format_func=lambda x: "เหมาเที่ยว (บาท/เที่ยว)" if x == "FLAT_RATE" else "บาทต่อตัน",
                              index=0 if init_method == "FLAT_RATE" else 1)
    
    freight_rate = st.number_input("อัตราค่าขนส่งเริ่มต้น (บาท)", min_value=0.0, step=10.0, value=init_rate)

    submitted = st.form_submit_button("💾 บันทึกข้อมูลรถ")
    if submitted:
        if not plate or not driver:
            st.error("❌ กรุณากรอกข้อมูล ทะเบียนรถ และ ชื่อคนขับ ด้วยครับ")
        else:
            truck_data = {
                "plate": plate,
                "driver_name": driver,
                "driver_phone": phone,
                "company": company,
                "empty_weight": empty_weight,
                "freight_method": freight_method,
                "freight_rate": freight_rate,
                "updated_at": "now()"
            }
            
            try:
                if selected_plate: # เคสแก้ไข
                    supabase.table("trucks").update(truck_data).eq("id", existing["id"]).execute()
                    st.success(f"🎉 อัปเดตข้อมูลรถ ทะเบียน {plate} เรียบร้อย!")
                else: # เคสเพิ่มใหม่
                    supabase.table("trucks").insert(truck_data).execute()
                    st.success(f"🎉 เพิ่มรถ ทะเบียน {plate} เข้าสู่ฐานข้อมูลเรียบร้อย!")
                st.rerun()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")

# ---- 4. ระบบลบข้อมูลรถ ----
if trucks_list:
    st.markdown("---")
    st.subheader("🗑️ ลบข้อมูลรถออกจากระบบ")
    delete_id = st.selectbox("เลือกคันที่ต้องการลบออกจากฐานข้อมูล", [t["id"] for t in trucks_list], 
                            format_func=lambda x: next(t["plate"] for t in trucks_list if t["id"] == x))
    if st.button("🗑️ ยืนยันการลบรถคันนี้เป็นการถาวร"):
        try:
            supabase.table("trucks").delete().eq("id", delete_id).execute()
            st.success("ลบข้อมูลรถเรียบร้อยแล้ว")
            st.rerun()
        except Exception as e:
            st.error(f"ไม่สามารถลบข้อมูลได้ (รถคันนี้อาจมีประวัติการวิ่งงานในตารางอื่นแล้ว): {e}")