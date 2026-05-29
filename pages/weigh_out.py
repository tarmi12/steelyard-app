import streamlit as st
from datetime import date
import qrcode
from io import BytesIO
from supabase import create_client, Client

st.header("⚖️ ชั่งออก (ตัดสต็อกหน้าลานลานเหล็กทันที)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ดึงคิวรถที่อยู่ระหว่างรอชั่งออกจริง (Status = PENDING)
try:
    load_res = supabase.table("load_orders").select("id, order_date, trucks(plate, driver_name), product_types(name)").eq("status", "PENDING").execute()
    orders_map = {f"คิวที่ {o['id']} - ทะเบียน {o['trucks']['plate']} ({o['product_types']['name']})": o for o in load_res.data}
except Exception as e:
    st.error(f"ไม่สามารถดึงข้อมูลคิวรถได้: {e}")
    orders_map = {}

# ดึงรายชื่อโรงงานปลายทางจริง
try:
    factory_res = supabase.table("factories").select("id, name").execute()
    factories_map = {f["name"]: f["id"] for f in factory_res.data}
except Exception:
    factories_map = {}

selected_label = st.selectbox("เลือกรายการสั่งโหลดรถที่จองคิวไว้", list(orders_map.keys()))

if selected_label:
    current_order = orders_map[selected_label]
    st.success(f"🚚 รถ: {current_order['trucks']['plate']} | คนขับ: {current_order['trucks']['driver_name']} | สินค้า: {current_order['product_types']['name']}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        gross = st.number_input("น้ำหนักรวมรถหนัก (Gross) kg", min_value=0, value=0, step=10)
    with col2:
        tare = st.number_input("น้ำหนักรถเปล่า (Tare) kg", min_value=0, value=0, step=10)
    with col3:
        net = gross - tare if gross >= tare else 0
        st.metric("น้ำหนักสินค้าสุทธิ (Net Weight)", f"{net:,} kg")
        
    dest_name = st.selectbox("เลือกโรงงานปลายทาง", list(factories_map.keys()))
    vat_mode = st.radio("ประเภทภาษี", ["NORMAL", "NO_VAT"])
    arrival_date = st.date_input("วันที่กำหนดถึงปลายทาง", date.today())
    remark = st.text_area("หมายเหตุการชั่งออก")
    
    if st.button("💾 บันทึกการชั่งออกและส่งข้อมูลพิมพ์", use_container_width=True):
        if net <= 0:
            st.error("น้ำหนักสินค้าไม่ถูกต้อง กรุณาตรวจสอบค่าน้ำหนักหนักและน้ำหนักเบาอีกครั้ง")
        else:
            try:
                insert_data = {
                    "load_order_id": current_order["id"],
                    "gross_weight": gross,
                    "tare_weight": tare,
                    "net_weight": net,
                    "vat_mode": vat_mode,
                    "destination_factory_id": factories_map[dest_name],
                    "arrival_date": str(arrival_date),
                    "remark": remark,
                    "created_by": st.session_state.user_id
                }
                
                res = supabase.table("weigh_out").insert(insert_data).execute()
                st.success("✅ บันทึกข้อมูลและทำรายการตัดสต็อก Physical เรียบร้อยแล้ว!")
                
                st.session_state.print_wo_id = res.data[0]["id"]
                st.session_state.print_data = {
                    "plate": current_order['trucks']['plate'],
                    "product": current_order['product_types']['name'],
                    "net": net,
                    "dest": dest_name
                }
                st.rerun()
            except Exception as error:
                st.error(f"เกิดข้อผิดพลาด: {error}")

# ---- ระบบจัดการเครื่องพิมพ์ผ่านหน้าต่างเบราว์เซอร์ (Window Print) ----
if "print_wo_id" in st.session_state:
    st.markdown("---")
    st.subheader("🖨️ ใบส่งสินค้า/ใบชั่งออก (สลิปขนาด 80mm)")
    
    p_data = st.session_state.print_data
    line_url = st.session_state.get("line_channel_token", "https://line.me")
    
    qr = qrcode.QRCode(version=1, box_size=4, border=1)
    qr.add_data(f"WO_ID:{st.session_state.print_wo_id}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    
    # แสดงสลีปจัดหน้าขนาดกะทัดรัดสำหรับเครื่องพิมพ์ความร้อน
    st.image(buf, width=150, caption="สแกนส่งหลักฐานปลายทาง")
    st.text(f"เลขที่เอกสารบิล: WO-{st.session_state.print_wo_id}")
    st.text(f"ทะเบียนรถ: {p_data['plate']}")
    st.text(f"ประเภทสินค้า: {p_data['product']}")
    st.text(f"น้ำหนักสุทธิ: {p_data['net']:,} kg")
    st.text(f"โรงงานปลายทาง: {p_data['dest']}")
    
    # ฝังคำสั่งควบคุมเบราว์เซอร์ให้เปิดหน้าต่างสั่งพิมพ์ทันที
    st.components.v1.html("""
        <script>
            window.parent.focus();
            window.print();
        </script>
    """, height=0, width=0)
    
    if st.button("❌ เสร็จสิ้นและปิดหน้าต่างพิมพ์"):
        del st.session_state.print_wo_id
        del st.session_state.print_data
        st.rerun()