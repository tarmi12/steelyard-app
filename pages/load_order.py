import streamlit as st
from datetime import date
from supabase import create_client, Client

st.header("🚚 สั่งโหลดเหล็กขึ้นรถ (จองคิวรถวิ่งงานจริง)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ---- 1. ดึงข้อมูลรถและประเภทสินค้าจาก Database จริง ----
try:
    truck_res = supabase.table("trucks").select("id, plate, driver_name, company, freight_method, freight_rate, empty_weight").execute()
    trucks_list = truck_res.data
    
    prod_res = supabase.table("product_types").select("id, name").execute()
    products = prod_res.data
except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลฐานข้อมูล: {e}")
    trucks_list, products = [], []

# ---- 2. ค้นหาและเลือกทะเบียนรถ ----
st.subheader("🔍 เลือกทะเบียนรถที่เข้าคิวงาน")
if not trucks_list:
    st.warning("⚠️ ยังไม่มีรถในระบบ กรุณาเพิ่มรถที่หน้าเมนู 'จัดการรถ/คนขับ' ก่อนครับ")
else:
    truck_options = {f"{t['plate']} | {t['company']} | คนขับ: {t['driver_name']}": t for t in trucks_list}
    selected_truck_label = st.selectbox("พิมพ์ค้นหาหรือเลือกทะเบียนรถ", list(truck_options.keys()))
    selected_truck = truck_options[selected_truck_label]

    st.markdown("---")
    
    # ---- 3. แสดงข้อมูลรถที่เลือกและกรอกสินค้าที่จะสั่งโหลด ----
    st.subheader("📦 รายละเอียดการสั่งโหลดงาน")
    
    with st.form("real_load_order_form"):
        col1, col2, col3 = st.columns(3)
        col1.metric("ทะเบียนรถ", selected_truck["plate"])
        col2.metric("คนขับรถ", selected_truck["driver_name"])
        col3.metric("น้ำหนักรถเปล่า (เริ่มต้น)", f"{selected_truck['empty_weight']:,} kg")
        
        st.write(f"**วิธีคิดค่าขนส่งเริ่มต้น:** {'เหมาเที่ยว' if selected_truck['freight_method'] == 'FLAT_RATE' else 'ราคาต่อตัน'} (อัตรา: {float(selected_truck['freight_rate']):,.2f} บาท)")
        st.markdown("---")
        
        # เลือกประเภทสินค้าจริงจากฐานข้อมูล
        prod_options = {p["name"]: p["id"] for p in products}
        selected_prod_name = st.selectbox("เลือกประเภทเหล็ก/สินค้าที่ต้องการโหลดขึ้นรถ", list(prod_options.keys()))
        
        # ปรับเปลี่ยนเรทค่าขนส่งหน้างานได้ เผื่อกรณีพิเศษ
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            freight_mode = st.radio("รูปแบบค่าขนส่งสำหรับเที่ยวนี้", ["FLAT_RATE", "PER_TON"],
                                    format_func=lambda x: "เหมาเที่ยว" if x == "FLAT_RATE" else "ต่อตันน้ำหนัก",
                                    index=0 if selected_truck["freight_method"] == "FLAT_RATE" else 1)
        with col_f2:
            freight_rate = st.number_input("แก้ไขอัตราค่าขนส่งเที่ยวนี้ (บาท)", min_value=0.0, value=float(selected_truck["freight_rate"]))
            
        base_weight_option = st.radio("กรณีคิดเงินต่อตัน ให้ใช้ฐานน้ำหนักจากที่ใด", ["ORIGIN", "DESTINATION"], 
                                      format_func=lambda x: "น้ำหนักต้นทาง (ลานเหล็กไทย)" if x == "ORIGIN" else "น้ำหนักปลายทาง (โรงงานรับซื้อ)",
                                      index=0)

        submitted = st.form_submit_button("✅ บันทึกใบสั่งโหลด (เปิดจองคิวรถ)")
        if submitted:
            try:
                load_order_data = {
                    "order_date": str(date.today()),
                    "truck_id": selected_truck["id"],
                    "product_type_id": prod_options[selected_prod_name],
                    "freight_mode": freight_mode,
                    "freight_rate": freight_rate,
                    "base_weight_option": base_weight_option if freight_mode == "PER_TON" else None,
                    "status": "PENDING",
                    "created_by": st.session_state.user_id
                }
                
                supabase.table("load_orders").insert(load_order_data).execute()
                st.success(f"🎉 ออกใบสั่งโหลดจองคิวให้รถทะเบียน {selected_truck['plate']} สำเร็จ! รถคันนี้จะไปปรากฏที่หน้าเมนู 'ชั่งออก' ทันทีครับ")
            except Exception as e:
                st.error(f"ไม่สามารถบันทึกข้อมูลใบสั่งโหลดได้: {e}")