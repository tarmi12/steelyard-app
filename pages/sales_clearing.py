import streamlit as st
from datetime import date
from supabase import create_client, Client

st.header("💰 เคลียร์บิลปลายทาง (บันทึกข้อมูลสรุปและตัดสต็อก Reporting)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ตัวแปรควบคุมการส่งข้อมูลซ้ำ
if "clearing_is_saving" not in st.session_state:
    st.session_state.clearing_is_saving = False

# ---- 1. ดึงข้อมูลรถชั่งออกที่ยังไม่เคยทำเรื่องเคลียร์บิลจริง ----
try:
    # ดึงข้อมูลละเอียดย้อนกลับไปหาตราชั่งต้นทางครบถ้วน
    wo_res = supabase.table("weigh_out").select(
        "id, gross_weight, tare_weight, net_weight, load_orders(trucks(plate), product_types(name)), factories(name)"
    ).execute()
    
    cleared_res = supabase.table("sales_clearing").select("weigh_out_id").execute()
    cleared_ids = [c["weigh_out_id"] for c in cleared_res.data]
    
    available_wo = {}
    for w in wo_res.data:
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
        st.subheader("⚖️ รายละเอียดค่าน้ำหนักเปรียบเทียบ ต้นทาง - ปลายทาง")
        
        # ⭐ [เพิ่มใหม่ตามสั่งการ] แสดงข้อมูลน้ำหนักตราชั่งต้นทางครบมิติในตารางกรอบสีแดง
        st.markdown("<div style='background-color:#fff0f0; padding:15px; border-radius:8px; border-left:6px solid #cc0000; margin-bottom:15px;'>", unsafe_allow_html=True)
        st.write("🔴 **ข้อมูลตราชั่งต้นทาง (ลานเหล็กไทย)**")
        col_o1, col_o2, col_o3 = st.columns(3)
        col_o1.write(f"• น้ำหนักรถหนัก (Gross ต้นทาง): **{wo['gross_weight']:,}** kg")
        col_o2.write(f"• น้ำหนักรถเปล่า (Tare ต้นทาง): **{wo['tare_weight']:,}** kg")
        col_o3.write(f"• น้ำหนักสินค้าสุทธิ (Net ต้นทาง): **{wo['net_weight']:,}** kg")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.write("🔵 **กรอกข้อมูลน้ำหนักปลายทาง (จากใบชั่งน้ำหนักของโรงงานรับซื้อ)**")
        
        # ย้ายช่องกรอกค่าน้ำหนักออกมานอก st.form เพื่อให้เกิดการคำนวณสดทันที (Live-Calculation)
        col1, col2 = st.columns(2)
        with col1:
            gross_dest = st.number_input("น้ำหนักรวมปลายทาง (Gross จากโรงงาน)", min_value=0, step=10, value=int(wo['gross_weight']))
        with col2:
            tare_dest = st.number_input("น้ำหนักรถเปล่าปลายทาง (Tare จากโรงงาน)", min_value=0, step=10, value=int(wo['tare_weight']))
            
        # สูตรประมวลผลคำนวณน้ำหนักปลายทางแบบเรียลไทม์
        net_dest = max(gross_dest - tare_dest, 0)
        
        st.markdown("---")
        col_res1, col_res2, col_res3 = st.columns(3)
        col_res1.metric("น้ำหนักสุทธิปลายทาง (Net)", f"{net_dest:,} kg")
        
        # คำนวณน้ำหนักขาดระหว่างทางสดทันที
        loss = wo['net_weight'] - net_dest
        if loss >= 0:
            col_res2.metric("🚨 น้ำหนักสูญหายระหว่างทาง", f"{loss:,} kg", delta=f"-{loss:,} kg", delta_color="inverse")
        else:
            col_res2.metric("✅ น้ำหนักเพิ่มขึ้นหน้างาน", f"{abs(loss):,} kg", delta=f"+{abs(loss):,} kg")
            
        impurity = st.number_input("หักน้ำหนักสิ่งเจือปนหน้าโรงงาน (Impurity kg)", min_value=0, step=1, value=0)
        net_billable = max(net_dest - impurity, 0)
        col_res3.metric("น้ำหนักสุทธิคิดเงิน (Net Billable)", f"{net_billable:,} kg")
        
        st.markdown("---")
        st.subheader("💵 เงื่อนไขราคาขายและข้อมูลทางบัญชี")
        
        # ย้ายส่วนคำนวณเงินออกมาอยู่นอกฟอร์มเพื่อแก้ไขปัญหาค่าเงินค้าง
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            sale_type = st.radio("ประเภทบิลคิดภาษีมูลค่าเพิ่ม", ["NORMAL", "NO_VAT"], format_func=lambda x: "ปกติ (มี VAT 7%)" if x=="NORMAL" else "นอกระบบ (No VAT)")
        with col_m2:
            price_per_ton = st.number_input("ราคาซื้อขายจริงต่อตัน (บาท)", min_value=0.0, step=100.0, value=12000.0)
            
        discount = st.number_input("ส่วนลดหน้าบิล (บาท)", min_value=0.0, step=10.0, value=0.0)
        remark = st.text_area("หมายเหตุประกอบการเคลียร์บิล")
        
        # ประมวลผลเงินรายรับและภาษีขายสดทันที
        sub_total = (net_billable / 1000) * price_per_ton - discount
        vat = round(sub_total * 0.07, 2) if sale_type == "NORMAL" else 0.0
        grand_total = sub_total + vat
        
        st.markdown("---")
        st.subheader("📋 ยอดรวมสุทธิที่ต้องเรียกเก็บจากโรงงาน")
        col_g1, col_g2 = st.columns(2)
        col_g1.metric("มูลค่าสินค้าก่อน VAT", f"{sub_total:,.2f} บาท")
        col_g2.metric("ยอดรวมสุทธิสุทธิ (Grand Total)", f"{grand_total:,.2f} บาท (Vat: {vat:,.2f})")
        
        # ครอบฟอร์มสั้น ๆ เฉพาะปุ่มบันทึก เพื่อทำหน้าที่ส่งข้อมูลลง Supabase ป้องกันกดย้ำอย่างปลอดภัย
        with st.form("secure_submit_only_form"):
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
        st.session_state.clearing_is_saving = False
        st.rerun()