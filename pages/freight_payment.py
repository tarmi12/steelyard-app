import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client

st.header("🚛 ระบบคำนวณรวมบิลจ่ายค่าขนส่งและอัปเดตสลิป (Freight Bulk Payment)")
st.info("📋 ระบบจัดการเงินสิบล้อ 2 ขั้นตอน: 1. ติ๊กเลือกรวมบิลส่งคิวเตรียมจ่าย ➡️ 2. โอนเงินสำเร็จแล้วกลับมาอัปเดตรหัสสลิปปิดงาน")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ตัวแปรควบคุมการส่งข้อมูลซ้ำ
if "freight_is_saving" not in st.session_state:
    st.session_state.freight_is_saving = False

# ดึงเกณฑ์คำนวณจากระบบตั้งค่าจริง
pct_threshold = float(st.session_state.get("transit_loss_threshold_percent", 0.5))
kg_threshold = int(st.session_state.get("transit_loss_threshold_kg", 50))
penalty_rate = float(st.session_state.get("penalty_rate_per_kg", 10.0))

# แบ่งกระดานทำงานเป็น 2 สเต็ปตามขั้นตอนจริง
tab1, tab2 = st.tabs(["📝 สเต็ปที่ 1: ติ๊กเลือกรวมบิลเตรียมจ่าย", "🖨️ สเต็ปที่ 2: อัปเดตเลขสลิปใบโอนเงิน"])

# =====================================================
# 📝 แท็บที่ 1: ติ๊กเลือกรวมบิลเตรียมจ่าย
# =====================================================
with tab1:
    try:
        # ดึงคิวรถที่ปิดงานขายจบแล้วทั้งหมด
        query_res = supabase.table("load_orders")\
            .select("id, freight_mode, freight_rate, base_weight_option, trucks(plate, driver_name, company), weigh_out(id, net_weight, destination_weigh_in(received_weight, impurity_kg))")\
            .eq("status", "COMPLETED").execute()
            
        # ดึงงานที่เคยจัดการไปแล้วมาคัดออก (ดูว่าอันไหนอยู่ในตาราง freight_payments แล้ว)
        managed_res = supabase.table("freight_payments").select("load_order_id, status").execute()
        managed_status_map = {m["load_order_id"]: m["status"] for m in managed_res.data}
        
        # กรองเอาเฉพาะเที่ยววิ่งที่สถานะเป็น 'UNPAID' (ยังไม่ได้ทำอะไรเลย)
        unpaid_jobs = []
        for job in query_res.data:
            status = managed_status_map.get(job["id"], "UNPAID")
            if status == "UNPAID" and job["weigh_out"] and job["weigh_out"][0]["destination_weigh_in"]:
                unpaid_jobs.append(job)
                
    except Exception as e:
        st.error(f"ไม่สามารถดึงเที่ยวงานค้างจ่ายได้: {e}")
        unpaid_jobs = []

    if not unpaid_jobs:
        st.success("🎉 ยอดเยี่ยม! รถวิ่งงานทุกคันถูกตั้งเรื่องเตรียมจ่ายหรือจ่ายเงินหมดแล้ว")
    else:
        st.subheader(f"📋 รายการเที่ยวรถค้างจ่ายเงินค่าน้ำมัน/ค่าขนส่ง ({len(unpaid_jobs)} เที่ยว)")
        st.caption("คำแนะนำ: ติ๊กถูกหน้าเที่ยวรถที่ต้องการนำมารวมบิลเพื่อกดส่งยอด 'เตรียมจ่าย'")
        
        selected_jobs = []
        total_freight_bulk = 0.0
        calculated_details = {} # เก็บค่าคำนวณไว้ใช้อัปเดตลงฐานข้อมูล
        
        # กางเช็คลิสต์รายเที่ยวรถ
        for job in unpaid_jobs:
            truck = job.get("trucks", {}) or {}
            company_name = truck.get("company") if truck.get("company") else "รถร่วม/ส่วนบุคคล" # [เพิ่มชื่อบริษัทขนส่งตามสั่งการ]
            plate = truck.get("plate", "-")
            driver = truck.get("driver_name", "-")
            
            wo_data = job["weigh_out"][0]
            dest_data = wo_data["destination_weigh_in"][0]
            
            # ตรรกะสูตรหักค่าน้ำหนักขาดตามเกณฑ์ลานเหล็ก
            net_origin = wo_data["net_weight"]
            net_dest = dest_data["received_weight"] if dest_data["received_weight"] else net_origin
            transit_loss = max(net_origin - net_dest, 0)
            
            max_loss_pct = (pct_threshold / 100) * net_origin
            max_allowed = min(max_loss_pct, kg_threshold)
            
            penalty = 0.0
            if transit_loss > max_allowed:
                excess_kg = transit_loss - max_allowed
                penalty = excess_kg * penalty_rate
                
            if job["freight_mode"] == "FLAT_RATE":
                freight_base = float(job["freight_rate"])
            else:
                weight_used = net_origin if job["base_weight_option"] == "ORIGIN" else net_dest
                freight_base = (weight_used / 1000) * float(job["freight_rate"])
                
            net_pay = max(freight_base - penalty, 0.0)
            
            # บันทึกค่าคำนวณลงตัวแปรดิบเตรียม Insert
            calculated_details[job["id"]] = {
                "calculated_freight": freight_base,
                "transit_loss_kg": transit_loss,
                "penalty": penalty,
                "net_pay": net_pay
            }
            
            # ข้อความแสดงรายระเอียดหน้าบิล [เพิ่มชื่อบริษัทขนส่งให้เห็นเด่นชัด]
            label_text = f" คิว LO-{job['id']} | 🏢 บริษัท: {company_name} | ทะเบียน: {plate} ({driver}) | 🔴 สุทธิลาน: {net_origin:,} kg ➡️ 🟢 ปลายทาง: {net_dest:,} kg | ⚠️ หักปรับ: {penalty:,.0f} บ. | 💵 ค่าขนส่งสุทธิ: {net_pay:,.2f} บาท"
            
            is_checked = st.checkbox(label_text, key=f"pay_job_{job['id']}")
            if is_checked:
                selected_jobs.append(job)
                total_freight_bulk += net_pay

        st.write("---")
        
        # เมื่อมีการติ๊กเลือกบิลรวมยอด
        if not selected_jobs:
            st.info("💡 กรุณาติ๊กเลือกรายการเที่ยวรถด้านบน เพื่อรวมบิลทำเรื่องเตรียมโอนเงิน")
        else:
            st.subheader("📊 ตรวจสอบสรุปยอดรวมบิลค่าขนส่ง (ก่อนกดส่งเตรียมจ่าย)")
            st.warning(f"จำนวนใบงานเที่ยวรถที่เลือกควบรวมบิล: **{len(selected_jobs)}** เที่ยว")
            st.metric("💰 ยอดเงินรวมทั้งหมดที่ต้องตั้งเรื่องโอนจ่ายสิบล้อ (บาท)", f"{total_freight_bulk:,.2f} บาท")
            
            # ปุ่มกดล็อกสถานะเตรียมจ่าย ป้องกันการกดย้ำอย่างปลอดภัย
            if st.button("⚙️ ยืนยันการรวมบิลและส่งรายชื่อไปที่หน้า 'เตรียมจ่าย'", use_container_width=True, disabled=st.session_state.freight_is_saving):
                st.session_state.freight_is_saving = True
                st.session_state.process_step = 1
                st.session_state.selected_jobs_data = [{
                    "load_order_id": j["id"],
                    "calculated_freight": calculated_details[j["id"]]["calculated_freight"],
                    "transit_loss_kg": calculated_details[j["id"]]["transit_loss_kg"],
                    "penalty": calculated_details[j["id"]]["penalty"],
                    "net_pay": calculated_details[j["id"]]["net_pay"],
                    "status": "PREPARED", # ล็อกไว้ว่าเตรียมจ่าย
                    "created_by": st.session_state.user_id
                } for j in selected_jobs]
                st.rerun()

# =====================================================
# 🖨️ แท็บที่ 2: อัปเดตเลขสลิปใบโอนเงิน (หน้าเตรียมจ่ายค้างอัปสลิป)
# =====================================================
with tab2:
    st.subheader("📥 รายการรวมบิลที่รอโอนเงินและอัปเดตหลักฐานสลิปธนาคาร")
    
    try:
        # ดึงข้อมูลจากตาราง freight_payments เฉพาะบิลที่จองคิวสถานะเป็น 'PREPARED' ไว้
        prepared_res = supabase.table("freight_payments")\
            .select("id, calculated_freight, penalty, net_pay, load_order_id, load_orders(trucks(plate, driver_name, company))")\
            .eq("status", "PREPARED").execute()
            
        prepared_list = prepared_res.data
    except Exception as e:
        prepared_list = []

    if not prepared_list:
        st.info("✨ ไม่มีบิลค้างในหน้าเตรียมจ่าย (ทุกเที่ยวรถโอนเงินและอัปเดตสลิปหมดเรียบร้อยแล้วครับ)")
    else:
        # จัดตารางใบงานที่เจ้าของลานคีย์รออัปเดตสลิปหลังโอนเงินเสร็จ
        prepared_rows = []
        for p in prepared_list:
            truck_info = p["load_orders"]["trucks"] if p["load_orders"] else {}
            prepared_rows.append({
                "รหัสตั้งจ่าย (ID)": p["id"],
                "คิววิ่งงาน": f"LO-{p['load_order_id']}",
                "บริษัทขนส่ง": truck_info.get("company", "รถร่วม"), # [เพิ่มชื่อบริษัทขนส่งตามสั่งการ]
                "ทะเบียนรถ": truck_info.get("plate", "-"),
                "คนขับรถ": truck_info.get("driver_name", "-"),
                "ค่าขนส่งเต็ม": f"{float(p['calculated_freight']):,.2f}",
                "โดนหักปรับ": f"{float(p['penalty']):,.2f}",
                "ยอดต้องโอนจริง": float(p["net_pay"])
            })
            
        df_prepared = pd.DataFrame(prepared_rows)
        st.dataframe(df_prepared, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.write("📝 **หลังจากโอนเงินผ่านแอปพลิเคชันธนาคารยอดรวมเสร็จแล้ว นำเลขบิลค้างมาอัปเดตสลิปที่นี่**")
        
        # ทำฟอร์มสั้นสำหรับอัปเดตรหัสโอนปิดงานรายคัน/รายกล่อง
        with st.form("upload_slip_form"):
            target_pay_id = st.selectbox("เลือก รหัสตั้งจ่าย (ID) หรือคิวงานที่จะอัปสลิปเงินโอน", [p["id"] for p in prepared_list])
            bank_ref_input = st.text_input("กรอกเลขที่อ้างอิงธนาคาร / รหัสสลิปโอนเงินสำเร็จ (Bank Ref) *")
            pay_method = st.radio("ช่องทางทำจ่าย", ["TRANSFER", "CASH"], format_func=lambda x: "โอนผ่านบัญชีธนาคาร" if x=="TRANSFER" else "จ่ายสด")
            payment_remark = st.text_area("หมายเหตุเพิ่มเติมประกอบการโอนเงิน")
            
            update_submitted = st.form_submit_button("✅ บันทึกอัปเดตสลิปโอนเงิน (ปิดบิลถาวร)")
            if update_submitted:
                if not bank_ref_input.strip() and pay_method == "TRANSFER":
                    st.error("❌ กรุณากรอกรหัสอ้างอิงสลิปโอนเงินธนาคารด้วยครับ")
                else:
                    st.session_state.freight_is_saving = True
                    st.session_state.process_step = 2
                    st.session_state.update_pay_id = target_pay_id
                    st.session_state.update_data = {
                        "bank_ref": bank_ref_input.strip() if bank_ref_input.strip() else "PAID_CASH",
                        "payment_method": pay_method,
                        "paid_date": str(date.today()),
                        "status": "PAID", # เปลี่ยนสถานะเป็นจ่ายเงินสำเร็จ
                        "remark": payment_remark
                    }
                    st.rerun()

# =====================================================
# 🚀 4. ส่วนประมวลผลคำสั่งฝั่งฐานข้อมูลจริง (หลังล็อกปุ่มกดย้ำ)
# =====================================================
if st.session_state.freight_is_saving:
    try:
        # เคสที่ 1: กดรวมบิลจากแท็บ 1 สั่งบันทึกตั้งเรื่อง PREPARED
        if st.session_state.get("process_step") == 1:
            for job_data in st.session_state.selected_jobs_data:
                supabase.table("freight_payments").insert(job_data).execute()
            st.success("🎉 ทำรายการควบรวมบิลและส่งยอดไปที่หน้า 'เตรียมจ่าย' สำเร็จ! สามารถไปตรวจสอบเพื่อโอนเงินต่อในแท็บที่ 2")
            
        # เคสที่ 2: กดอัปเดตสลิปจากแท็บ 2 สั่งปิดบิลเป็น PAID
        elif st.session_state.get("process_step") == 2:
            supabase.table("freight_payments").update(st.session_state.update_data).eq("id", st.session_state.update_pay_id).execute()
            st.success("🎉 อัปเดตสลิปและบันทึกปิดยอดบัญชีค่าขนส่งสำเร็จบิลเรียบร้อย!")
            st.balloons()
            
    except Exception as error:
        st.error(f"เกิดข้อผิดพลาดกับระบบฐานข้อมูล: {error}")
    finally:
        # ล้างสถานะเพื่อปลดล็อกปุ่มกดรอบถัดไป
        st.session_state.freight_is_saving = False
        if "selected_jobs_data" in st.session_state: del st.session_state.selected_jobs_data
        if "update_data" in st.session_state: del st.session_state.update_data
        st.rerun()