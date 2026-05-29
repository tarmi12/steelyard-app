import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.header("🚘 จัดการข้อมูลรถและคนขับ (ระบบใช้งานจริง)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ตัวแปรควบคุมการบันทึกซ้ำ
if "truck_is_saving" not in st.session_state:
    st.session_state.truck_is_saving = False

# ---- 1. ดึงข้อมูลรถทั้งหมดจากฐานข้อมูลจริง ----
try:
    truck_res = supabase.table("trucks").select("*").order("plate").execute()
    trucks_list = truck_res.data
except Exception as e:
    st.error(f"ไม่สามารถดึงข้อมูลรถได้: {e}")
    trucks_list = []

# ---- 2. แสดงตารางรถปัจจุบัน ----
st.subheader("📋 รายการรถในระบบปัจจุบัน")
if not trucks_list:
    st.info("ยังไม่มีข้อมูลรถในระบบ กรุณาเพิ่มข้อมูลด้านล่าง")
else:
    df = pd.DataFrame([{
        "ID": t["id"],
        "ทะเบียน": t["plate"],
        "คนขับ": t["driver_name"],
        "เบอร์โทร": t["driver_phone"] or "-",
        "บริษัทขนส่ง": t["company"] or "-",
        "น้ำหนักเบา (kg)": t["empty_weight"],
        "รูปแบบค่าขนส่ง": "เหมาเที่ยว" if t["freight_method"] == "FLAT_RATE" else "ต่อตันน้ำหนัก",
        "อัตราค่าขนส่ง": f"{float(t['freight_rate']):,.2f}",
        "ฐานน้ำหนัก (กรณีคิดต่อตัน)": "ต้นทาง (ลานเหล็ก)" if t.get("base_weight_option") == "ORIGIN" else ("ปลายทาง (โรงงาน)" if t.get("base_weight_option") == "DESTINATION" else "ไม่ได้ตั้งค่า")
    } for t in trucks_list])
    st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("---")

# ---- 3. ฟอร์ม เพิ่ม / แก้ไข ข้อมูลรถ ----
st.subheader("➕ เพิ่ม / แก้ไข ข้อมูลรถและเรทค่าขนส่งประจำรถ")
with st.form("real_truck_form"):
    truck_plates = [""] + [t["plate"] for t in trucks_list]
    selected_plate = st.selectbox("เลือกทะเบียนรถเพื่อแก้ไข (หากต้องการเพิ่มใหม่ให้ปล่อยว่าง)", truck_plates)

    if selected_plate:
        existing = next(t for t in trucks_list if t["plate"] == selected_plate)
        init_plate = existing["plate"]
        init_driver = existing["driver_name"]
        init_phone = existing["driver_phone"] or ""
        init_company = existing["company"] or ""
        init_empty = existing["empty_weight"] or 0
        init_method = existing["freight_method"]
        init_rate = float(existing["freight_rate"])
        # ป้องกันกรณีที่ดึงมาแล้วเจอค่า None หรือค่าว่างเปล่า
        init_base = existing.get("base_weight_option") if existing.get("base_weight_option") else "ORIGIN"
    else:
        init_plate, init_driver, init_phone, init_company, init_empty, init_method, init_rate, init_base = "", "", "", "", 0, "FLAT_RATE", 0.0, "ORIGIN"

    plate = st.text_input("ทะเบียนรถ *", value=init_plate)
    col1, col2 = st.columns(2)
    with col1:
        driver = st.text_input("ชื่อคนขับ *", value=init_driver)
        phone = st.text_input("เบอร์โทรคนขับ", value=init_phone)
    with col2:
        company = st.text_input("บริษัทขนส่ง/สังกัด", value=init_company)
        empty_weight = st.number_input("น้ำหนักรถเปล่าเริ่มต้น (kg)", min_value=0, value=init_empty, step=10)

    st.markdown("---")
    st.write("📋 **ตั้งค่าเงื่อนไขการคิดเงินและเรทค่าขนส่งประจำรถคันนี้**")
    
    freight_method = st.radio("รูปแบบค่าขนส่งสำหรับเที่ยวนี้", ["FLAT_RATE", "PER_TON"], 
                              format_func=lambda x: "เหมาเที่ยว" if x == "FLAT_RATE" else "ต่อตันน้ำหนัก",
                              index=0 if init_method == "FLAT_RATE" else 1)
    
    freight_rate = st.number_input("แก้ไขอัตราค่าขนส่งเที่ยวนี้ (บาท)", min_value=0.0, step=10.0, value=init_rate)

    base_weight_option = st.radio("กรณีคิดเงินต่อตัน ให้ใช้ฐานน้ำหนักจากที่ใด", ["ORIGIN", "DESTINATION"],
                                  format_func=lambda x: "น้ำหนักต้นทาง (ลานเหล็กไทย)" if x == "ORIGIN" else "น้ำหนักปลายทาง (โรงงานรับซื้อ)",
                                  index=0 if init_base == "ORIGIN" else 1)

    st.markdown("---")
    
    # ระบบควบคุมการส่งข้อมูลซ้ำ
    submit_disabled = st.session_state.truck_is_saving
    btn_label = "⌛ กำลังบันทึกข้อมูลรถ..." if st.session_state.truck_is_saving else "💾 บันทึกข้อมูลรถ"
    
    submitted = st.form_submit_button(btn_label, disabled=submit_disabled)
    if submitted:
        if not plate.strip() or not driver.strip():
            st.error("❌ กรุณากรอกข้อมูล ทะเบียนรถ และ ชื่อคนขับ ด้วยครับ")
        else:
            st.session_state.truck_is_saving = True
            st.rerun()

# ---- 4. ส่วนประมวลผลบันทึกจริงลงฐานข้อมูล ----
if st.session_state.truck_is_saving:
    try:
        truck_data = {
            "plate": plate.strip(),
            "driver_name": driver.strip(),
            "driver_phone": phone.strip() if phone.strip() else None,
            "company": company.strip() if company.strip() else None,
            "empty_weight": empty_weight,
            "freight_method": freight_method,
            "freight_rate": freight_rate,
            "base_weight_option": base_weight_option if freight_method == "PER_TON" else None
        }
        
        if selected_plate:
            supabase.table("trucks").update(truck_data).eq("id", existing["id"]).execute()
            st.success(f"🎉 อัปเดตข้อมูลรถ ทะเบียน {plate} เรียบร้อย!")
        else:
            # ตรวจสอบทะเบียนซ้ำก่อน INSERT เพื่อความปลอดภัย
            check_dup = supabase.table("trucks").select("id").eq("plate", plate.strip()).execute()
            if check_dup.data:
                st.error(f"❌ ไม่สามารถเพิ่มได้ เนื่องจากมีทะเบียนรถ {plate} อยู่ในระบบแล้ว")
            else:
                supabase.table("trucks").insert(truck_data).execute()
                st.success(f"🎉 เพิ่มรถ ทะเบียน {plate} เรียบร้อย!")
            
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
    finally:
        st.session_state.truck_is_saving = False
        st.rerun()

# ---- 5. ระบบลบข้อมูลรถ ----
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
            st.error(f"ไม่สามารถลบข้อมูลได้เนื่องจากรถคันนี้มีประวัติวิ่งงานแล้ว: {e}")