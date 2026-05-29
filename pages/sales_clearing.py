import streamlit as st
from datetime import date
from supabase import create_client, Client

st.header("💰 เคลียร์บิลปลายทาง (บันทึกข้อมูลสรุปและตัดสต็อก Reporting)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ตัวแปรควบคุมการส่งข้อมูลซ้ำ (Anti-Duplicate Switch)
if "clearing_is_saving" not in st.session_state:
    st.session_state.clearing_is_saving = False

# ---- 1. ดึงข้อมูลรถชั่งออกที่ยังไม่เคยทำเรื่องเคลียร์บิลจริง ----
try:
    # ดึงข้อมูลจากตาราง weigh_out โดยเชื่อมข้อมูลรถยนต์ ประเภทสินค้า และโรงงาน
    wo_res = supabase.table("weigh_out").select(
        "id, net_weight, load_orders(trucks(plate), product_types(name)), factories(name)"
    ).execute()
    
    # ดึงข้อมูลไอดีบิลที่เคลียร์จบไปแล้วมาเช็คตัดออก
    cleared_res = supabase.table("sales_clearing").select("weigh_out_id").execute()
    cleared_ids = [c["weigh_out_id"] for c in cleared_res.data]
    
    # ทำการกรองเอาเฉพาะบิลชั่งออกที่ยังตกค้าง (ยังไม่ได้เคลียร์บิล)
    available_wo = {}
    for w in wo_res.data:
        # ป้องกันกรณีที่โครงสร้างข้อมูล Join แล้วส่งค่ากลับมาเป็น None
        if w["id"] in cleared_ids:
            continue
            
        load_order = w.get("load_orders")
        truck_plate = load_order["trucks"]["plate"] if load_order and load_order.get("trucks") else "ไม่ระบุทะเบียน"
        prod_name = load_order["product_types"]["name"] if load_order and load_order.get("product_types") else "ไม่ระบุสินค้า"
        factory_name = w["factories"]["name"] if w.get("factories") else "ไม่ระบุโรงงาน"
        
        label = f"บิลชั่งออก WO-{w['id']} | รถ {truck_plate} ({factory_name}) - เหล็ก: {prod_name}"
        available_wo[label] = w

except Exception as e:
    st.error(f"ไม่สามารถดึงข้อมูลรายการเคลียร์บิลได้: {e}")
    available_wo = {}

# ---- 2. แสดงตัวเลือกรายการบิลบนหน้าจอ ----
if not available_wo:
    st.info("✨ ไม่มีรายการบิลชั่งออกค้างเคลียร์ในระบบ (รถทุกคันทำเรื่องเคลียร์ยอดหมดแล้วครับ)")
else:
    selected_label = st.selectbox("เลือกเอกสารใบชั่งออกที่ต้องการเคลียร์ยอดบิลค้าส่ง", list(available_wo.keys()))
    
    if selected_label:
        wo = available_wo[selected_label]
        
        st.markdown("---")
        st.subheader("⚖️ รายละเอียดและผลต่างน้ำหนักจริง")
        st.write(f"**น้ำหนักสุทธิจากต้นทาง (ลานเหล็กไทย):** {wo['net_weight']:,} kg")
        
        with st.form("real_sales_clearing_form"):
            col1, col2 = st.columns(2)
            with col1:
                gross_dest = st.number_input("น้ำหนักรวมปลายทาง (Gross จากโรงงาน)", min_value=0, step=10, value=int(wo['net_weight'] + 5000))
            with col2:
                tare_dest = st.number_input("น้ำหนักรถเปล่าปลายทาง (Tare จากโรงงาน)", min_value=0, step=10, value=5000)
                
            net_dest = gross_dest - tare_dest if gross_dest >= tare_dest else 0
            st.metric("น้ำหนักสุทธิปลายทาง (Net Destination)", f"{net_dest:,} kg")
            
            loss = wo['net_weight'] - net_dest
            if loss >= 0:
                st.warning(f"🚨 น้ำหนักสูญหายระหว่างขนส่ง: {loss:,} kg")
            else:
                st.success(f"✅ น้ำหนักเพิ่มขึ้น: {abs(loss):,} kg")
                
            impurity = st.number_input("หักน้ำหนักสิ่งเจือปนหน้าโรงงาน (Impurity kg)", min_value=0, step=1, value=0)
            net_billable = max(net_dest - impurity, 0)
            st.metric("น้ำหนักสุทธิรวมคิดเงิน (Net Billable Weight)", f"{net_billable:,} kg")
            
            st.markdown("---")
            sale_type = st.radio("ประเภทบิลคิดภาษีมูลค่าเพิ่ม", ["NORMAL", "NO_VAT"], format_func=lambda x: "ปกติ (มี VAT 7%)" if x=="NORMAL" else "นอกระบบ (No VAT)")
            price_per_ton = st.number_input("ราคาซื้อขายจริงต่อตัน (บาท)", min_value=0.0, step=100.0, value=12000.0)
            discount = st.number_input("ส่วนลดหน้าบิล (บาท)", min_value=0.0, step=10.0, value=0.0)
            remark = st.text_area("หมายเหตุประกอบการเคลียร์บิล")
            
            # คำนวณรายรับและภาษีมูลค่าเพิ่มจริง
            sub_total = (net_billable / 1000) * price_per_ton - discount
            vat = round(sub_total * 0.07, 2) if sale_type == "NORMAL" else 0.0
            grand_total = sub_total + vat
            
            st.write("---")
            st.subheader("📋 ยอดรวมสุทธิที่ต้องเรียกเก็บจากโรงงาน")
            col_g1, col_g2 = st.columns(2)
            col_g1.metric("มูลค่าสินค้าก่อน VAT", f"{sub_total:,.2f} บาท")
            col_g2.metric("ยอดรวมสุทธิสุทธิ (Grand Total)", f"{grand_total:,.2f} บาท (Vat: {vat:,.2f})")
            
            # ระบบควบคุมปุ่มบันทึกซ้ำ
            submit_disabled = st.session_state.clearing_is_saving
            btn_label = "⌛ กำลังอัปเดตระบบบัญชีสต็อกคู่..." if st.session_state.clearing_is_saving else "✅ ยืนยันปิดบิลและตัดยอดบัญชีสต็อกคู่"
            
            submitted = st.form_submit_button(btn_label, disabled=submit_disabled)
            if submitted:
                if net_dest <= 0:
                    st.error("❌ ค่าน้ำหนักปลายทางไม่ถูกต้อง กรุณาตรวจสอบน้ำหนักรถหนักและรถเบาอีกครั้ง")
                else:
                    st.session_state.clearing_is_saving = True
                    st.rerun()

# ---- 3. ส่วนประมวลผลบันทึกข้อมูลจริงลงฐานข้อมูล ----
if st.session_state.clearing_is_saving:
    try:
        # ดึงบิลปัจจุบันกลับมาใช้อ้างอิงหลังจากการรีรันหน้าจอ
        wo_id_target = wo["id"]
        
        # 1. บันทึกน้ำหนักและผลตรวจสอบปลายทางลงตาราง destination_weigh_in
        supabase.table("destination_weigh_in").insert({
            "weigh_out_id": wo_id_target,
            "received_weight": net_dest,
            "impurity_kg": impurity,
            "net_billable_weight": net_billable,
            "scan_method": "Manual",
            "remark": remark if remark.strip() else None
        }).execute()
        
        # 2. บันทึกยอดตั้งลูกหนี้ในตารางการเงิน sales_clearing
        # (ขั้นตอนนี้จะไปปลุกให้ Trigger หลังบ้านทำงานเพื่อตัดสต็อกฝั่ง REPORTING ทันที)
        supabase.table("sales_clearing").insert({
            "weigh_out_id": wo_id_target,
            "sale_type": sale_type,
            "final_price_per_ton": price_per_ton,
            "total_amount": sub_total,
            "vat_amount": vat,
            "discount": discount,
            "clearing_date": str(date.today()),
            "remark": remark if remark.strip() else None,
            "created_by": st.session_state.user_id
        }).execute()
        
        st.success("🎉 บันทึกการเคลียร์บิลปลายทาง และตัดสต็อกบัญชีฝั่ง Reporting สำเร็จเรียบร้อย!")
        st.balloons()
        
    except Exception as error:
        st.error(f"ไม่สามารถบันทึกรายการเคลียร์บิลได้เนื่องจาก: {error}")
    finally:
        # ปลดล็อกระบบป้องกันการบันทึกซ้ำ
        st.session_state.clearing_is_saving = False
        st.rerun()