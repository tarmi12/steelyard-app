import streamlit as st
from datetime import date
from supabase import create_client, Client

st.header("⚖️ ระบบบันทึกน้ำหนักชั่งออก (ตัดสต็อกคลังสินค้ากองจริง)")
st.info("🔴 ข้อมูลน้ำหนักสุทธิหน้าลานจะถูกนำไปหักออกจากสต็อกคลังกองจริง (Physical Stock) ทันทีหลังกดบันทึก")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ตัวแปรควบคุมการส่งข้อมูลซ้ำ (Anti-Duplicate Switch)
if "weigh_out_is_saving" not in st.session_state:
    st.session_state.weigh_out_is_saving = False

# ---- 1. ดึงข้อมูลคิวรถที่ค้างชั่งออก (แก้จุดค้างถาวร) ----
try:
    # 1.1 ดึงคิวรถที่สถานะยังเป็น PENDING ทั้งหมดจากฐานข้อมูล
    lo_res = supabase.table("load_orders").select("id, truck_id, product_type_id, order_date").eq("status", "PENDING").execute()
    pending_orders = lo_res.data
    
    # 1.2 ดึงข้อมูล Master รถยนต์ทั้งหมดเพื่อเอามาจับคู่ชื่อ
    truck_res = supabase.table("trucks").select("id, plate, driver_name, empty_weight").execute()
    truck_map = {t["id"]: t for t in truck_res.data}
    
    # 1.3 ดึงข้อมูล Master ประเภทเหล็กทั้งหมดมาจับคู่ชื่อ
    prod_res = supabase.table("product_types").select("id, name").execute()
    prod_map = {p["id"]: p["name"] for p in prod_res.data}
    
    # 1.4 ดึงข้อมูลโรงงานปลายทางทั้งหมดมาทำตัวเลือกให้เสมียนจิ้มเลือก
    factory_res = supabase.table("factories").select("id, name").execute()
    factory_options = {f["name"]: f["id"] for f in factory_res.data}
    
    # นำข้อมูล Master ทั้งหมดมาจัดรูปทำเป็นกล่องตัวเลือกคิวรถค้างชั่งบนหน้าจอ
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

# ---- 2. แสดงผลฟอร์มตราชั่งหน้าลาน ----
if not available_queues:
    st.success("✨ ไม่มีรถยนต์ตกค้างในคิวชั่งออก (รถทุกคันผ่านเครื่องชั่งและวิ่งออกจากลานหมดแล้วครับ)")
else:
    selected_label = st.selectbox("เลือกคิวรถสิบล้อที่เหยียบอยู่บนเครื่องตราชั่งออก", list(available_queues.keys()))
    
    if selected_label:
        current_job = available_queues[selected_label]
        
        st.markdown("---")
        st.subheader("📝 กรอกข้อมูลพิกัดน้ำหนักจากตราชั่งจริง")
        
        # ดึงค่าน้ำหนักรถเปล่าเริ่มต้นมาคำนวณเปรียบเทียบ
        default_tare = current_job["truck_empty_weight"]
        
        # ปรับระบบเป็นคำนวณสดนอกฟอร์ม (Live-Calculation) เพื่อไม่ให้สูตรคำนวณค้างแบบหน้าเคลียร์บิล
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            gross_input = st.number_input("1. น้ำหนักรวมรถหนัก (Gross Weight - kg) *", min_value=0, step=10, value=int(default_tare + 15000))
        with col_w2:
            tare_input = st.number_input("2. น้ำหนักรถเปล่าหน้างาน (Tare Weight - kg) *", min_value=0, step=10, value=int(default_tare))
            
        # สูตรคำนวณหาน้ำหนักเนื้อเหล็กสุทธิสดๆ ทันที
        net_weight_calc = max(gross_input - tare_input, 0)
        
        st.markdown("---")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("📦 น้ำหนักสินค้าสุทธิที่จะหักสต็อก (Net Weight)", f"{net_weight_calc:,} kg")
        with col_m2:
            # เลือกโรงงานปลายทางที่จะไปส่ง
            selected_factory_name = st.selectbox("เลือกโรงงานปลายทางผู้รับซื้อสินค้าเที่ยวนี้ *", list(factory_options.keys()))
            
        remark = st.text_area("หมายเหตุประกอบการชั่งน้ำหนักขาออก")
        
        st.markdown("---")
        
        # ครอบฟอร์มเฉพาะปุ่มบันทึก เพื่อทำหน้าที่สั่ง INSERT ลงระบบอย่างปลอดภัยกันกดย้ำ
        with st.form("secure_weigh_out_submit"):
            submit_disabled = st.session_state.weigh_out_is_saving
            btn_label = "⌛ กำลังตัดสต็อกหน้าลานเรียบลอย..." if st.session_state.weigh_out_is_saving else "⚖️ ยืนยันบันทึกน้ำหนักและตัดสต็อกคลังจริงทันที"
            
            submitted = st.form_submit_button(btn_label, disabled=submit_disabled)
            if submitted:
                if net_weight_calc <= 0:
                    st.error("❌ ค่าน้ำหนักสินค้าไม่ถูกต้อง น้ำหนักรถหนักต้องมากกว่าน้ำหนักรถเปล่าครับ")
                else:
                    st.session_state.weigh_out_is_saving = True
                    st.rerun()

# ---- 3. ส่วนประมวลผลคำสั่งฝั่งฐานข้อมูลจริง (หลังผ่านระบบล็อกปุ่ม) ----
if st.session_state.weigh_out_is_saving:
    try:
        target_lo_id = current_job["load_order_id"]
        target_factory_id = factory_options[selected_factory_name]
        
        # 3.1 บันทึกข้อมูลตราชั่งลงตาราง weigh_out เพื่อเปิดใบสลิปออกลาน
        # (ขั้นตอนนี้จะไปปลุกตัว Trigger หลังบ้านให้ทำการหักลบยอดสต็อกฝั่ง PHYSICAL ทันที)
        supabase.table("weigh_out").insert({
            "load_order_id": target_lo_id,
            "gross_weight": gross_input,
            "tare_weight": tare_input,
            "net_weight": net_weight_calc,
            "destination_factory_id": target_factory_id,
            "weigh_out_date": str(date.today()),
            "remark": remark if remark.strip() else None,
            "created_by": st.session_state.user_id
        }).execute()
        
        # 3.2 ทำการอัปเดตสถานะคิวงานหลักใน load_orders จาก PENDING ให้เปลี่ยนเป็น IN_TRANSIT (อยู่ระหว่างเดินทาง)
        supabase.table("load_orders").update({"status": "IN_TRANSIT"}).eq("id", target_lo_id).execute()
        
        st.success(f"🎉 บันทึกชั่งออกคิว LO-{target_lo_id} สำเร็จ! ตัดสต็อกหน้าลานจริงเรียบร้อย และส่งรายชื่อรถคันนี้เข้าสู่ 'กระดานติดตามรถระหว่างเดินทาง' ทันทีครับ")
        st.balloons()
        
    except Exception as error:
        st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูลชั่งออก: {error}")
    finally:
        # ปลดล็อกปุ่มให้พนักงานชั่งรถคันถัดไปได้ปกติ
        st.session_state.weigh_out_is_saving = False
        st.rerun()