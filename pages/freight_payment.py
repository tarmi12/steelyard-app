import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client

st.header("🚛 ระบบคำนวณและจ่ายค่าขนส่งให้รถสิบล้อ (อิงเกณฑ์ปรับจริง)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ---- 1. ดึงเกณฑ์ควบคุมค่าปรับจากระบบตั้งค่าจริง ----
pct_threshold = float(st.session_state.get("transit_loss_threshold_percent", 0.5))
kg_threshold = int(st.session_state.get("transit_loss_threshold_kg", 50))
penalty_rate = float(st.session_state.get("penalty_rate_per_kg", 10.0))

st.info(f"⚙️ **เกณฑ์ปัจจุบัน:** หายได้ไม่เกิน **{pct_threshold}%** หรือสูงสุดไม่เกิน **{kg_threshold} kg** | เกินเกณฑ์ปรับ **{penalty_rate} บาท/kg**")

# ---- 2. ดึงข้อมูลรถวิ่งงานที่เคลียร์บิลแล้ว แต่ยังไม่ได้จ่ายค่าขนส่ง (Status ใน freight_payments เป็น UNPAID หรือยังไม่มีคิวจ่าย) ----
try:
    # ดึงข้อมูลจาก load_orders -> weigh_out -> destination_weigh_in เฉพาะคันที่ COMPLETED แล้ว
    query_res = supabase.table("load_orders")\
        .select("id, freight_mode, freight_rate, base_weight_option, trucks(plate, driver_name, company), weigh_out(id, net_weight, destination_weigh_in(received_weight, impurity_kg, remark))")\
        .eq("status", "COMPLETED").execute()
        
    # ดึงคิวที่เคยจ่ายเงินไปแล้วมากันออก
    paid_res = supabase.table("freight_payments").select("load_order_id").eq("status", "PAID").execute()
    paid_ids = [p["load_order_id"] for p in paid_res.data]
    
    # กรองเอาเฉพาะเที่ยวงานที่ยังไม่จ่ายเงินค้างจ่าย
    unpaid_jobs = []
    for job in query_res.data:
        if job["id"] not in paid_ids and job["weigh_out"] and job["weigh_out"][0]["destination_weigh_in"]:
            unpaid_jobs.append(job)
            
except Exception as e:
    st.error(f"ไม่สามารถดึงเที่ยวงานค้างจ่ายได้: {e}")
    unpaid_jobs = []

# ---- 3. แสดงรายการงานที่ค้างจ่ายเงิน ----
st.subheader("📋 รายการเที่ยวรถที่รออนุมัติจ่ายค่าขนส่ง")
if not unpaid_jobs:
    st.success("✅ ยอดเยี่ยม! ไม่มียอดค้างจ่ายค่าขนส่งสิบล้อในระบบแล้ว")
else:
    display_rows = []
    for j in unpaid_jobs:
        wo_data = j["weigh_out"][0]
        dest_data = wo_data["destination_weigh_in"][0]
        transit_loss = max(wo_data["net_weight"] - dest_data["received_weight"], 0)
        
        display_rows.append({
            "Load ID": j["id"],
            "ทะเบียน": j["trucks"]["plate"],
            "คนขับ": j["trucks"]["driver_name"],
            "รูปแบบ": "เหมา" if j["freight_mode"] == "FLAT_RATE" else "ต่อตัน",
            "เรทค่าขนส่ง": f"{float(j['freight_rate']):,.2f}",
            "นน.ต้นทาง (kg)": wo_data["net_weight"],
            "นน.ปลายทาง (kg)": dest_data["received_weight"],
            "น้ำหนักขาด (kg)": transit_loss,
            "หักสิ่งเจือปน (kg)": dest_data["impurity_kg"]
        })
    st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

    # ให้เสมียนเลือกเลขคิวรถที่จะทำจ่ายเงิน
    selected_id = st.selectbox("เลือกเลขคิวงานที่ต้องการคำนวณเงินจ่าย", [j["id"] for j in unpaid_jobs])
    
    if selected_id:
        target_job = next(j for j in unpaid_jobs if j["id"] == selected_id)
        wo_data = target_job["weigh_out"][0]
        dest_data = wo_data["destination_weigh_in"][0]
        
        # คำนวณสูตรคณิตศาสตร์เรื่องน้ำหนักหายและค่าปรับ
        net_origin = wo_data["net_weight"]
        net_dest = dest_data["received_weight"]
        transit_loss = max(net_origin - net_dest, 0)
        
        # หาเกณฑ์ที่ยอมรับได้สูงสุด
        max_loss_pct = (pct_threshold / 100) * net_origin
        max_allowed = min(max_loss_pct, kg_threshold)
        
        # คำนวณค่าปรับกรณีน้ำหนักหายเกินเกณฑ์
        penalty = 0.0
        if transit_loss > max_allowed:
            excess_kg = transit_loss - max_allowed
            penalty = excess_kg * penalty_rate
            
        # คำนวณค่าขนส่งก่อนหัก
        if target_job["freight_mode"] == "FLAT_RATE":
            freight_base = float(target_job["freight_rate"])
            weight_used = None
        else:
            weight_used = net_origin if target_job["base_weight_option"] == "ORIGIN" else net_dest
            freight_base = (weight_used / 1000) * float(target_job["freight_rate"])
            
        net_pay = max(freight_base - penalty, 0.0)
        
        # แสดงใบบันทึกผลลัพธ์การเงินคันนี้
        st.markdown("---")
        st.subheader(f"💸 ใบบันทึกการหักเงินคิวรถเลขที่ {selected_id}")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.write(f"**รถทะเบียน:** {target_job['trucks']['plate']} ({target_job['trucks']['company']})")
            st.write(f"**ค่าขนส่งตั้งต้น:** {freight_base:,.2f} บาท")
            if weight_used:
                st.write(f"*(คำนวณจากฐานน้ำหนัก {weight_used:,} kg)*")
            st.write(f"**น้ำหนักขาดหน้างาน:** {transit_loss} kg (เกณฑ์ยอมรับได้ {max_allowed:.1f} kg)")
            st.error(f"⚠️ **ยอดรวมค่าปรับหักน้ำหนักขาด:** {penalty:,.2f} บาท")
        with col_b:
            st.metric("ยอดรวมสุทธิที่ต้องโอนให้คนขับ (Net Pay)", f"{net_pay:,.2f} บาท", delta=f"-{penalty:,.2f} บาท")
            
        # ฟอร์มยืนยันตัดเงินในบัญชีจริง
        with st.form("real_freight_payment_form"):
            payment_method = st.radio("ช่องทางการจ่ายเงิน", ["TRANSFER", "CASH"], format_func=lambda x: "โอนผ่านธนาคาร" if x=="TRANSFER" else "เงินสด")
            bank_ref = st.text_input("เลขที่อ้างอิงการโอนเงิน/เลขที่สลิป (กรณีโอนเงิน)")
            payment_remark = st.text_area("หมายเหตุการจ่ายเงินค่าขนส่ง")
            
            submitted = st.form_submit_button("✅ ยืนยันการโอนเงินสำเร็จและบันทึกปิดงาน")
            if submitted:
                try:
                    payment_data = {
                        "load_order_id": selected_id,
                        "calculated_freight": freight_base,
                        "transit_loss_kg": transit_loss,
                        "penalty": penalty,
                        "net_pay": net_pay,
                        "payment_method": payment_method,
                        "bank_ref": bank_ref if payment_method=="TRANSFER" else None,
                        "paid_date": str(date.today()),
                        "status": "PAID",
                        "remark": payment_remark,
                        "created_by": st.session_state.user_id
                    }
                    
                    supabase.table("freight_payments").insert(payment_data).execute()
                    st.success("🎉 บันทึกประวัติการจ่ายเงินค่าขนส่งเข้าสู่ฐานข้อมูลเรียบร้อย คิวรถคันนี้เคลียร์ยอดสำเร็จ!")
                    st.rerun()
                except Exception as e:
                    st.error(f"ไม่สามารถบันทึกการชำระเงินได้: {e}")