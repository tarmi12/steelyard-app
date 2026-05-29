import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client

st.header("💵 ตรวจสอบและบันทึกเงินโอนจากโรงงาน (ระบบเคลียร์ยอดรวมหลายบิล)")
st.info("📋 โรงงานโอนเงินรวมยอดมาหลายบิล? คุณสามารถติ๊กเลือกหน้ารายการบิลที่โอนรวมกันมาด้านล่างนี้ ระบบจะคำนวณยอดเงินรวมให้อัตโนมัติ")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ตัวแปรควบคุมการส่งข้อมูลซ้ำ (Anti-Duplicate Switch)
if "receipt_is_saving" not in st.session_state:
    st.session_state.receipt_is_saving = False

# ---- 1. ดึงรายการเคลียร์บิลที่ "ยังไม่ได้รับเงิน" หรือค้างจ่ายทั้งหมด ----
try:
    # ดึงรายการ sales_clearing ที่เชื่อมข้อมูลรถยนต์ และโรงงานปลายทาง
    clearing_res = supabase.table("sales_clearing").select(
        "id, weigh_out_id, total_amount, vat_amount, clearing_date, "
        "weigh_out(net_weight, load_orders(trucks(plate), product_types(name)), factories(name))"
    ).order("id", desc=True).execute()
    
    # ดึงรายการที่เคยบันทึกรับเงินไปแล้วในตาราง receipts เพื่อเอามาคัดออก
    receipts_res = supabase.table("receipts").select("sales_clearing_id").eq("status", "RECEIVED").execute()
    paid_clearing_ids = [r["sales_clearing_id"] for r in receipts_res.data]
    
    # กรองเฉพาะรายการที่โรงงานยังค้างจ่ายเงินอยู่จริง ๆ
    unpaid_list = [c for c in clearing_res.data if c["id"] not in paid_clearing_ids]
except Exception as e:
    st.error(f"ไม่สามารถดึงข้อมูลบิลค้างรับเงินได้: {e}")
    unpaid_list = []
    paid_clearing_ids = []

# ---- 2. แสดงตารางรายการบิลค้างจ่าย เพื่อให้เลือกติ๊ก (Checkbox) ----
if not unpaid_list:
    st.success("🎉 ยอดเยี่ยม! โรงงานปลายทางชำระเงินครบถ้วนทุกบิลแล้ว ไม่มีค้างยอดลูกหนี้")
else:
    st.subheader(f"📋 รายการบิลค้างชำระทั้งหมด ณ ปัจจุบัน ({len(unpaid_list)} บิล)")
    st.caption("คำแนะนำ: ติ๊กถูก หน้าช่องบิลที่โรงงานระบุในใบแจ้งยอดโอนเงิน")

    selected_clearing_records = []
    total_calculated_amount = 0.0

    # สร้างแบบฟอร์มกางตารางสำหรับเลือกบิลแบบยืดหยุ่น
    for bill in unpaid_list:
        wo_data = bill.get("weigh_out", {}) or {}
        load_order = wo_data.get("load_orders", {}) or {}
        truck_plate = load_order.get("trucks", {}).get("plate", "ไม่ระบุ")
        factory_name = wo_data.get("factories", {}).get("name", "ไม่ระบุ")
        prod_name = load_order.get("product_types", {}).get("name", "ไม่ระบุ")
        
        # คำนวณยอดสุทธิรวม VAT ประจำบิลใบนี้
        bill_grand_total = float(bill["total_amount"]) + float(bill["vat_amount"])
        
        # ทำข้อความระบุรายละเอียดบิลรายบรรทัด
        label_text = f" บิล SC-{bill['id']} | โรงงาน: {factory_name} | รถ: {truck_plate} ({prod_name}) | วันที่เคลียร์: {bill['clearing_date']} | ยอดเงิน: {bill_grand_total:,.2f} บาท"
        
        # สร้าง Checkbox รายบิลบนหน้าจอ
        is_selected = st.checkbox(label_text, key=f"select_sc_{bill['id']}")
        
        if is_selected:
            selected_clearing_records.append(bill)
            total_calculated_amount += bill_grand_total

    st.markdown("---")

    # ---- 3. สรุปยอดเงินและฟอร์มการบันทึกเมื่อมีการเลือกบิล ----
    if not selected_clearing_records:
        st.info("💡 กรุณาติ๊กเลือกรายการบิลค้างจ่ายด้านบนอย่างน้อย 1 รายการเพื่อเริ่มทำเรื่องบันทึกรับเงิน")
    else:
        st.subheader("💰 สรุปรายละเอียดการรับเงินโอนรวมยอด")
        st.warning(f"คุณเลือกเคลียร์บิลพร้อมกันทั้งหมด **{len(selected_clearing_records)}** รายการ")
        
        # แสดงยอดเงินที่ระบบคำนวณรวมกันจากทุกบิลที่ติ๊ก
        st.metric(" ยอดเงินรวมที่คำนวณตามบิล (Total Amount)", f"{total_calculated_amount:,.2f} บาท")
        
        with st.form("bulk_receipt_form"):
            st.write("📝 **กรอกข้อมูลอ้างอิงจากสลิปโอนเงินธนาคาร**")
            
            # ช่องกรอกจำนวนเงินโอนเข้าจริง เผื่อกรณีโรงงานโอนขาดหรือโอนเกินจากยอดบิลเล็กน้อย
            received_amount_input = st.number_input("จำนวนเงินรวมที่โอนเข้าบัญชีจริงตามสลิป (บาท) *", 
                                                    min_value=0.0, value=total_calculated_amount, step=100.0)
            bank_ref = st.text_input("เลขที่อ้างอิงธนาคาร / รหัสสลิปโอนเงิน (Bank Ref) *")
            receipt_date = st.date_input("วันที่เงินโอนเข้าบัญชี", date.today())
            payment_remark = st.text_area("หมายเหตุการรับเงินรวมยอด (เช่น โอนรวมยอดสัปดาห์ที่ 2)")

            # ระบบควบคุมปุ่มบันทึกซ้ำ
            submit_disabled = st.session_state.receipt_is_saving
            btn_label = "⌛ กำลังตัดยอดบัญชีลูกหนี้..." if st.session_state.receipt_is_saving else "✅ ยืนยันเงินเข้าบัญชีและปิดบิลทั้งหมดที่เลือก"
            
            submitted = st.form_submit_button(btn_label, disabled=submit_disabled)
            if submitted:
                if not bank_ref.strip():
                    st.error("❌ กรุณากรอกเลขที่อ้างอิงธนาคารหรือรหัสสลิปโอนเงินเพื่อความปลอดภัยของบัญชี")
                else:
                    st.session_state.receipt_is_saving = True
                    st.rerun()

# ---- 4. ส่วนประมวลผลบันทึกจริงลงฐานข้อมูลแบบรวดเดียวครบทุกบิล ----
if st.session_state.receipt_is_saving:
    try:
        # คำนวณสัดส่วนเฉลี่ยยอดเงินโอนจริงแบ่งเข้าแต่ละบิล (กรณีโรงงานโอนมาตรงยอด ยอดจะหารลงตัวพอดี)
        # แต่เพื่อตรรกะระบบ เราจะวนลูป INSERT ปิดสถานะตาราง receipts ทีละบิลตามรายการที่เสมียนติ๊กไว้ครับ
        for bill in selected_clearing_records:
            bill_grand_total = float(bill["total_amount"]) + float(bill["vat_amount"])
            
            # สั่ง INSERT บันทึกแยกรายบิลใน Supabase เพื่อเปลี่ยนสถานะเป็นชำระเงินแล้ว
            supabase.table("receipts").insert({
                "sales_clearing_id": bill["id"],
                "received_amount": bill_grand_total, # บันทึกปิดยอดเต็มจำนวนของบิลนั้นๆ
                "bank_ref": bank_ref.strip(),
                "receipt_date": str(receipt_date),
                "status": "RECEIVED",
                "created_by": st.session_state.user_id
            }).execute()
            
        st.success(f"🎉 สำเร็จ! ระบบได้ทำการบันทึกรับเงินและปิดยอดหนี้สะสมทั้ง {len(selected_clearing_records)} บิลเข้าสู่ฐานข้อมูลเรียบร้อยแล้ว!")
        st.balloons()
        
    except Exception as error:
        st.error(f"ไม่สามารถบันทึกข้อมูลการรับเงินรวมยอดได้เนื่องจาก: {error}")
    finally:
        st.session_state.receipt_is_saving = False
        st.rerun()