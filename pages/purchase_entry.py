import streamlit as st
from datetime import date
from supabase import create_client, Client

st.header("📥 บันทึกซื้อเข้าสิ้นวัน (ระบบบันทึกจริงลงฐานข้อมูล)")
st.info("🔴 สีแดง = Physical | 🔵 สีน้ำเงิน = Reporting (ข้อมูลจะถูกส่งเข้าตารางธุรกรรมสต็อกโดยอัตโนมัติ)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ---- 1. ตัวแปรควบคุมการส่งข้อมูลซ้ำ (Anti-Duplicate Switch) ----
if "entry_is_saving" not in st.session_state:
    st.session_state.entry_is_saving = False

# ดึงรายการประเภทสินค้าจริงจากฐานข้อมูล
try:
    product_res = supabase.table("product_types").select("id, name").execute()
    product_options = {p["name"]: p["id"] for p in product_res.data}
except Exception as e:
    st.error(f"ไม่สามารถเชื่อมต่อประเภทสินค้าได้: {e}")
    product_options = {}

if "rows_count" not in st.session_state:
    st.session_state.rows_count = 1

if st.button("➕ เพิ่มแถวรายการสินค้า"):
    st.session_state.rows_count += 1

form_data = []

# ---- 2. ฟอร์มกรอกข้อมูลการซื้อ ----
with st.form("real_purchase_entry_form"):
    purchase_date = st.date_input("วันที่ซื้อสินค้า", date.today())
    st.markdown("---")
    
    for i in range(st.session_state.rows_count):
        cols = st.columns([2, 1.2, 1.2, 1.2, 1.2])
        with cols[0]:
            p_name = st.selectbox("ประเภทสินค้า", list(product_options.keys()), key=f"prod_name_{i}")
        with cols[1]:
            p_w = st.number_input("🔴 นน.Physical (kg)", min_value=0, step=1, key=f"real_pw_{i}")
        with cols[2]:
            p_p = st.number_input("🔴 ราคา/ตัน Phys", min_value=0.0, step=10.0, key=f"real_pp_{i}")
        with cols[3]:
            r_w = st.number_input("🔵 นน.Reporting (kg)", min_value=0, step=1, key=f"real_rw_{i}")
        with cols[4]:
            r_p = st.number_input("🔵 ราคา/ตัน Rep", min_value=0.0, step=10.0, key=f"real_rp_{i}")
            
        form_data.append({
            "product_type_id": product_options.get(p_name), # เปลี่ยนเป็น product_type_id เรียบร้อย
            "physical_weight": p_w,
            "physical_price_per_ton": p_p,
            "reporting_weight": r_w,
            "reporting_price_per_ton": r_p
        })

    st.markdown("---")
    
    # ---- 3. จัดการปุ่มบันทึกเพื่อควบคุมการกดย้ำ (Debounce Control) ----
    submit_disabled = st.session_state.entry_is_saving
    btn_label = "⌛ กำลังบันทึกข้อมูลเข้าฐานข้อมูลและสต็อกคู่..." if st.session_state.entry_is_saving else "✅ ยืนยันบันทึกข้อมูลลงระบบจริง"
    
    submitted = st.form_submit_button(btn_label, disabled=submit_disabled)
    
    if submitted:
        if not form_data or any(item["physical_weight"] == 0 for item in form_data):
            st.error("❌ กรุณากรอกข้อมูลน้ำหนักสินค้าให้ถูกต้องและครบถ้วนก่อนบันทึก")
        else:
            # เปิดสวิตช์ล็อกทันทีเมื่อกดครั้งแรก และสั่งรีเฟรชหน้าจอเพื่อปิดใช้งานปุ่ม
            st.session_state.entry_is_saving = True
            st.rerun()

# ---- 4. ส่วนประมวลผลเมื่อปุ่มถูกล็อก (ดึงงานส่งไปบันทึกจริงที่ Supabase) ----
if st.session_state.entry_is_saving:
    try:
        # 1. บันทึกข้อมูลใบซื้อหลัก (Header)
        order_insert = supabase.table("purchase_orders").insert({
            "purchase_date": str(purchase_date),
            "created_by": st.session_state.user_id
        }).execute()
        
        po_id = order_insert.data[0]["id"]
        
        # 2. บันทึกข้อมูลรายการสินค้า (Line Items)
        for item in form_data:
            item["purchase_order_id"] = po_id
            supabase.table("purchase_lines").insert(item).execute()
        
        st.success(f"🎉 บันทึกใบซื้อเลขที่ {po_id} เรียบร้อย สต็อกคู่ทั้งสองระบบอัปเดตแล้ว!")
        st.balloons()
        
        # ล้างจำนวนแถวกลับไปเป็น 1 แถวเริ่มต้น
        st.session_state.rows_count = 1
        
    except Exception as error:
        st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {error}")
    finally:
        # ปลดล็อกปุ่มให้เสมียนสามารถคีย์บิลใบถัดไปได้ตามปกติ
        st.session_state.entry_is_saving = False
        st.rerun()