import streamlit as st
from datetime import date
from supabase import create_client, Client

st.header("💰 เคลียร์บิลปลายทาง (บันทึกข้อมูลสรุปและตัดสต็อก Reporting)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ดึงข้อมูลรถชั่งออกที่ยังไม่เคยทำเรื่องเคลียร์บิลจริง
try:
    wo_res = supabase.table("weigh_out").select("id, net_weight, load_orders(trucks(plate), product_types(name)), factories(name)").execute()
    cleared_res = supabase.table("sales_clearing").select("weigh_out_id").execute()
    cleared_ids = [c["weigh_out_id"] for c in cleared_res.data]
    
    available_wo = {f"บิลชั่งออก WO-{w['id']} - รถ {w['load_orders']['trucks']['plate']} ({w['factories']['name']})": w 
                    for w in wo_res.data if w["id"] not in cleared_ids}
except Exception as e:
    st.error(f"ไม่สามารถดึงข้อมูลรายการเคลียร์บิลได้: {e}")
    available_wo = {}

selected_label = st.selectbox("เลือกเอกสารใบชั่งออกที่ต้องการเคลียร์ยอดบิลค้าส่ง", list(available_wo.keys()))

if selected_label:
    wo = available_wo[selected_label]
    
    st.subheader("⚖️ รายละเอียดและผลต่างน้ำหนักจริง")
    st.write(f"**น้ำหนักสุทธิจากต้นทาง (ลานเหล็กไทย):** {wo['net_weight']:,} kg")
    
    with st.form("real_sales_clearing_form"):
        col1, col2 = st.columns(2)
        with col1:
            gross_dest = st.number_input("น้ำหนักรวมปลายทาง (Gross จากโรงงาน)", min_value=0, step=10)
        with col2:
            tare_dest = st.number_input("น้ำหนักรถเปล่าปลายทาง (Tare จากโรงงาน)", min_value=0, step=10)
            
        net_dest = gross_dest - tare_dest if gross_dest >= tare_dest else 0
        st.metric("น้ำหนักสุทธิปลายทาง (Net Destination)", f"{net_dest:,} kg")
        
        loss = wo['net_weight'] - net_dest
        if loss >= 0:
            st.warning(f"🚨 น้ำหนักสูญหายระหว่างขนส่ง: {loss:,} kg")
        else:
            st.success(f"✅ น้ำหนักเพิ่มขึ้น: {abs(loss):,} kg")
            
        impurity = st.number_input("หักน้ำหนักสิ่งเจือปนหน้าโรงงาน (Impurity kg)", min_value=0, step=1)
        net_billable = max(net_dest - impurity, 0)
        st.metric("น้ำหนักสุทธิรวมคิดเงิน (Net Billable Weight)", f"{net_billable:,} kg")
        
        st.markdown("---")
        sale_type = st.radio("ประเภทบิลคิดภาษีมูลค่าเพิ่ม", ["NORMAL", "NO_VAT"])
        price_per_ton = st.number_input("ราคาซื้อขายจริงต่อตัน (บาท)", min_value=0.0, step=100.0)
        discount = st.number_input("ส่วนลดหน้าบิล (บาท)", min_value=0.0, step=10.0)
        remark = st.text_area("หมายเหตุประกอบการเคลียร์บิล")
        
        # คำนวณรายรับและภาษีมูลค่าเพิ่มจริง
        sub_total = (net_billable / 1000) * price_per_ton - discount
        vat = round(sub_total * 0.07, 2) if sale_type == "NORMAL" else 0.0
        grand_total = sub_total + vat
        
        st.metric("ยอดสุทธิที่ต้องเรียกเก็บจากโรงงาน (Grand Total)", f"{grand_total:,.2f} บาท (Vat: {vat:,.2f})")
        
        submitted = st.form_submit_button("✅ ยืนยันปิดบิลและตัดยอดบัญชีสต็อกคู่")
        
        if submitted:
            try:
                # 1. บันทึกน้ำหนักและผลตรวจสอบปลายทาง
                supabase.table("destination_weigh_in").insert({
                    "weigh_out_id": wo["id"],
                    "received_weight": net_dest,
                    "impurity_kg": impurity,
                    "net_billable_weight": net_billable,
                    "scan_method": "Manual",
                    "remark": remark
                }).execute()
                
                # 2. บันทึกยอดตั้งลูกหนี้ในตารางการเงิน
                supabase.table("sales_clearing").insert({
                    "weigh_out_id": wo["id"],
                    "sale_type": sale_type,
                    "final_price_per_ton": price_per_ton,
                    "total_amount": sub_total,
                    "vat_amount": vat,
                    "discount": discount,
                    "clearing_date": str(date.today()),
                    "remark": remark,
                    "created_by": st.session_state.user_id
                }).execute()
                
                st.success("🎉 บันทึกการเคลียร์บิลและตัดสต็อกฝั่ง Reporting เรียบร้อยแล้ว!")
                st.rerun()
            except Exception as error:
                st.error(f"ไม่สามารถทำรายการได้: {error}")