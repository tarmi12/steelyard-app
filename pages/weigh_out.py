import streamlit as st
from datetime import date
from supabase import create_client, Client

st.header("⚖️ ระบบบันทึกน้ำหนักชั่งออก (ตัดสต็อกคลังสินค้ากองจริง)")
st.info("🔴 ข้อมูลน้ำหนักสุทธิหน้าลานจะถูกนำไปหักออกจากสต็อกคลังกองจริง (Physical Stock) ทันทีหลังกดบันทึก")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ตัวแปรควบคุมปุ่มบันทึกเพื่อป้องกันการส่งซ้ำ
if "is_weigh_out_processing" not in st.session_state:
    st.session_state.is_weigh_out_processing = False

# ---- 1. ดึงข้อมูลคิวรถที่ค้างชั่งออก ----
try:
    lo_res = supabase.table("load_orders").select("id, truck_id, product_type_id, order_date").eq("status", "PENDING").execute()
    pending_orders = lo_res.data
    
    truck_res = supabase.table("trucks").select("id, plate, driver_name, empty_weight").execute()
    truck_map = {t["id"]: t for t in truck_res.data}
    
    prod_res = supabase.table("product_types").select("id, name").execute()
    prod_map = {p["id"]: p["name"] for p in prod_res.data}
    
    factory_res = supabase.table("factories").select("id, name").execute()
    factory_options = {f["name"]: f["id"] for f in factory_res.data}
    
    available_queues = {}
    for lo in pending_orders:
        truck_data = truck_map.get(lo["truck_id"], {})
        plate = truck_data.get("plate", "ไม่ระบุทะเบียน")
        driver = truck_data.get("driver_name", "ไม่ระบุคนขับ")
        prod_name = prod_map.get(lo["product_type_id"], "ไม่ระบุประเภทเหล็ก")
        
        label = f"คิวจอง LO-{lo['id']} | รถทะเบียน: {plate} ({driver}) - เหล็ก: {prod_name}"
        available_queues[label] = {
            "load_order_id": lo["id"],
            "truck_id": lo["truck_id"],
            "product_type_id": lo["product_type_id"],
            "truck_empty_weight": truck_data.get("empty_weight", 0)
        }

except Exception as e:
    st.error(f"ไม่สามารถเชื่อมต่อข้อมูลคิวตราชั่งได้: {e}")
    available_queues = {}
    factory_options = {}

# ---- 2. แสดงผลฟอร์มกรอกและคำนวณน้ำหนักสด ----
if not available_queues:
    st.success("✨ ไม่มีรถยนต์ตกค้างในคิวชั่งออก (รถทุกคันผ่านเครื่องชั่งและวิ่งออกจากลานหมดแล้วครับ)")
else:
    selected_label = st.selectbox("เลือกคิวรถสิบล้อที่เหยียบอยู่บนเครื่องตราชั่งออก", list(available_queues.keys()))
    
    if selected_label:
        current_job = available_queues[selected_label]
        
        st.markdown("---")
        st.subheader("📝 กรอกข้อมูลพิกัดน้ำหนักจากตราชั่งจริง")
        
        # ค่าน้ำหนักเริ่มต้นเป็น 0 เคลียร์ ๆ ตามหน้าตราชั่งจริง
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            gross_input = st.number_input("1. น้ำหนักรวมรถหนัก (Gross Weight - kg) *", min_value=0, step=10, value=0)
        with col_w2:
            tare_input = st.number_input("2. น้ำหนักรถเปล่าหน้างาน (Tare Weight - kg) *", min_value=0, step=10, value=0)
            
        net_weight_calc = max(gross_input - tare_input, 0)
        
        st.markdown("---")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("📦 น้ำหนักสินค้าสุทธิที่จะหักสต็อก (Net Weight)", f"{net_weight_calc:,} kg")
        with col_m2:
            selected_factory_name = st.selectbox("เลือกโรงงานปลายทางผู้รับซื้อสินค้าเที่ยวนี้ *", list(factory_options.keys()))
            
        # ⭐️ [เพิ่มใหม่ตามสั่งการ] กล่องเลือกประเภท VAT เพื่อส่งค่าเข้าฐานข้อมูลโดยตรง ไม่ต้องเดาสุ่ม
        st.markdown("---")
        st.subheader("📊 เงื่อนไขภาษีสำหรับตั๋วชั่งใบนี้")
        user_vat_mode = st.radio(
            "กรุณาเลือกประเภทระบบภาษีมูลค่าเพิ่ม (VAT Mode) *", 
            ["NORMAL", "NO_VAT"], 
            format_func=lambda x: "ปกติ (มี VAT 7%)" if x == "NORMAL" else "นอกระบบ (No VAT / ไม่คิดภาษี)"
        )
        
        remark = st.text_area("หมายเหตุประกอบการชั่งน้ำหนักขาออก")
        st.markdown("---")
        
        # ---- 3. จัดการปุ่มบันทึกแบบ Single-Step ----
        btn_label = "⌛ กำลังบันทึกและตัดสต็อก..." if st.session_state.is_weigh_out_processing else "⚖️ ยืนยันบันทึกน้ำหนักและตัดสต็อกคลังจริงทันที"
        
        if st.button(btn_label, use_container_width=True, disabled=st.session_state.is_weigh_out_processing):
            if gross_input <= 0 or tare_input <= 0:
                st.error("❌ กรุณากรอกค่าน้ำหนักรถหนักและรถเบาให้ครบถ้วนก่อนกดบันทึก")
            elif net_weight_calc <= 0:
                st.error("❌ ค่าน้ำหนักสินค้าไม่ถูกต้อง น้ำหนักรวมรถหนักต้องมีมากกว่าน้ำหนักรถเปล่าครับ")
            else:
                st.session_state.is_weigh_out_processing = True
                
                try:
                    target_lo_id = current_job["load_order_id"]
                    target_factory_id = factory_options[selected_factory_name]
                    
                    # บันทึกข้อมูลเข้าตาราง weigh_out โดยนำค่า user_vat_mode ที่เสมียนติ๊กเลือกส่งไปบันทึกจริง
                    supabase.table("weigh_out").insert({
                        "load_order_id": target_lo_id,
                        "gross_weight": gross_input,
                        "tare_weight": tare_input,
                        "net_weight": net_weight_calc,
                        "destination_factory_id": target_factory_id,
                        "vat_mode": user_vat_mode, # บันทึกตามที่พนักงานติ๊กเลือกจริงหน้างานผ่านฉลุย
                        "date": str(date.today()),
                        "remark": remark if remark.strip() else None,
                        "created_by": st.session_state.user_id
                    }).execute()
                    
                    # ปรับสถานะใบสั่งคิวหลักเป็น IN_TRANSIT
                    supabase.table("load_orders").update({"status": "IN_TRANSIT"}).eq("id", target_lo_id).execute()
                    
                    st.success(f"🎉 สำเร็จ! บันทึกน้ำหนักบิล {target_lo_id} เรียบร้อย (ระบบ: {user_vat_mode}) ยอดรถเด้งเข้าแผงมอนิเตอร์ทันทีครับ")
                    st.balloons()
                    
                    st.session_state.is_weigh_out_processing = False
                    st.rerun()
                    
                except Exception as error:
                    st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูลจริงสู่ฐานข้อมูล: {error}")
                    st.session_state.is_weigh_out_processing = False