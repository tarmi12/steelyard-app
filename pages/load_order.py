import streamlit as st
from datetime import date
from supabase import create_client, Client

st.header("🚚 สั่งโหลดเหล็กขึ้นรถ (จองคิวรถวิ่งงานจริง)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ตัวแปรควบคุมการบันทึกซ้ำ
if "load_is_saving" not in st.session_state:
    st.session_state.load_is_saving = False

# ---- 1. ดึงข้อมูลรถและประเภทสินค้าจาก Database จริง ----
try:
    truck_res = supabase.table("trucks").select("id, plate, driver_name, company, freight_method, freight_rate, empty_weight, base_weight_option").execute()
    trucks_list = truck_res.data
    
    prod_res = supabase.table("product_types").select("id, name").execute()
    products = prod_res.data
except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
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
    
    # ---- 3. ฟอร์มการสั่งโหลดงานแบบรวดเร็ว ----
    st.subheader("📦 รายละเอียดการสั่งโหลดงาน")
    
    with st.form("real_load_order_form"):
        col1, col2, col3 = st.columns(3)
        col1.metric("ทะเบียนรถ", selected_truck["plate"])
        col2.metric("คนขับรถ", selected_truck["driver_name"])
        col3.metric("น้ำหนักรถเปล่า (เริ่มต้น)", f"{selected_truck['empty_weight']:,} kg")
        
        # แสดงให้เสมียนรับรู้เรทที่ย้ายไปตั้งค่าหลังบ้าน
        method_th = "เหมาเที่ยว" if selected_truck['freight_method'] == 'FLAT_RATE' else "ต่อตันน้ำหนัก"
        base_th = "ต้นทาง" if selected_truck.get('base_weight_option') == 'ORIGIN' else "ปลายทาง"
        st.info(f"💰 **เรทราคาประจำรถคันนี้:** คิดเงินแบบ **{method_th}** อัตรา **{float(selected_truck['freight_rate']):,.2f}** บาท " + 
                (f"(ใช้ฐานน้ำหนัก: **{base_th}**)" if selected_truck['freight_method'] == 'PER_TON' else ""))
        
        st.markdown("---")
        
        # เลือกประเภทสินค้าจริงจากฐานข้อมูล
        prod_options = {p["name"]: p["id"] for p in products}
        selected_prod_name = st.selectbox("เลือกประเภทเหล็ก/สินค้าที่ต้องการโหลดขึ้นรถ", list(prod_options.keys()))

        # จัดการปุ่มบันทึกเพื่อควบคุมการกดย้ำ
        submit_disabled = st.session_state.load_is_saving
        btn_label = "⌛ กำลังเปิดบิลจองคิวรถ..." if st.session_state.load_is_saving else "✅ บันทึกใบสั่งโหลด (เปิดจองคิวรถ)"
        
        submitted = st.form_submit_button(btn_label, disabled=submit_disabled)
        if submitted:
            st.session_state.load_is_saving = True
            st.rerun()

# ---- 4. ส่วนประมวลผลบันทึกจริงลงฐานข้อมูล ----
if st.session_state.load_is_saving:
    try:
        # ดึงค่าอัตราและเงื่อนไขการคิดเงินจากตัวแปรประจำรถคันที่เลือกมา Insert โดยตรง
        load_order_data = {
            "order_date": str(date.today()),
            "truck_id": selected_truck["id"],
            "product_type_id": prod_options[selected_prod_name],
            "freight_mode": selected_truck["freight_method"],
            "freight_rate": selected_truck["freight_rate"],
            "base_weight_option": selected_truck.get("base_weight_option"),
            "status": "PENDING",
            "created_by": st.session_state.user_id
        }
        
        supabase.table("load_orders").insert(load_order_data).execute()
        st.success(f"🎉 ออกใบสั่งโหลดให้รถ {selected_truck['plate']} สำเร็จ! รถคันนี้ส่งคิวไปที่หน้าเมนู 'ชั่งออก' เรียบร้อยครับ")
        
    except Exception as e:
        st.error(f"ไม่สามารถบันทึกข้อมูลใบสั่งโหลดได้: {e}")
    finally:
        st.session_state.load_is_saving = False
        st.rerun()