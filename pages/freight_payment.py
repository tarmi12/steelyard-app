import streamlit as st
import pandas as pd
from datetime import date

st.header("🚛 จ่ายค่าขนส่งให้สิบล้อ (Freight Payment)")

# --- จำลองข้อมูล Load Order ที่เสร็จแล้วและยังไม่ได้จ่าย ---
demo_loads = [
    {
        "load_id": "LO0001",
        "truck": "80-1234",
        "driver": "สมชาย",
        "company": "สมชายขนส่ง",
        "freight_mode": "FLAT_RATE",
        "rate": 3000.00,
        "base_weight_option": None,
        "net_origin": 15300,
        "net_dest": 15000,
        "transit_loss": 300,
        "impurity_kg": 50,
        "clearing_remark": "ฝนตก น้ำหนักเพิ่ม",
        "status": "UNPAID"
    },
    {
        "load_id": "LO0002",
        "truck": "80-5678",
        "driver": "สมศักดิ์",
        "company": "ศักดิ์ขนส่ง",
        "freight_mode": "PER_TON",
        "rate": 100.00,
        "base_weight_option": "ORIGIN",
        "net_origin": 16200,
        "net_dest": 16000,
        "transit_loss": 200,
        "impurity_kg": 30,
        "clearing_remark": "",
        "status": "UNPAID"
    },
    {
        "load_id": "LO0003",
        "truck": "80-9999",
        "driver": "สมบัติ",
        "company": "บัติโลจิสติกส์",
        "freight_mode": "PER_TON",
        "rate": 110.00,
        "base_weight_option": "DESTINATION",
        "net_origin": 14000,
        "net_dest": 13800,
        "transit_loss": 200,
        "impurity_kg": 0,
        "clearing_remark": "ไม่มี",
        "status": "UNPAID"
    }
]

# --- ดึงค่าตั้งต้นจาก settings (จำลอง) ---
transit_loss_threshold_pct = 0.5  # 0.5%
transit_loss_threshold_kg = 50    # 50 กก.
penalty_rate_per_kg = 10.0        # บาท ต่อ กก. ที่เกิน

st.subheader("📋 รายการ Load Order ที่พร้อมจ่ายค่าขนส่ง")

df = pd.DataFrame([
    {
        "Load ID": l["load_id"],
        "ทะเบียน": l["truck"],
        "คนขับ": l["driver"],
        "บริษัท": l["company"],
        "รูปแบบ": "เหมา" if l["freight_mode"] == "FLAT_RATE" else "ต่อตัน",
        "อัตรา": f"{l['rate']:,.2f}",
        "ฐานน้ำหนัก": l["base_weight_option"] if l["freight_mode"] == "PER_TON" else "-",
        "ต้นทาง(kg)": l["net_origin"],
        "ปลายทาง(kg)": l["net_dest"],
        "หาย(kg)": l["transit_loss"],
        "Impurity(kg)": l["impurity_kg"],
        "หมายเหตุเคลียร์": l["clearing_remark"]
    } for l in demo_loads
])
st.dataframe(df, use_container_width=True)

st.markdown("---")

selected_ids = st.multiselect(
    "เลือก Load Order ที่ต้องการจ่าย (สามารถจ่ายหลายเที่ยวพร้อมกัน)",
    [l["load_id"] for l in demo_loads]
)

if selected_ids:
    selected_loads = [l for l in demo_loads if l["load_id"] in selected_ids]

    payment_details = []
    total_net_pay = 0.0

    for load in selected_loads:
        # คำนวณค่าขนส่งตามรูปแบบ
        if load["freight_mode"] == "FLAT_RATE":
            freight = load["rate"]
            weight_used = None
        else:  # PER_TON
            # เลือกน้ำหนักตาม base_weight_option
            if load["base_weight_option"] == "ORIGIN":
                weight_used = load["net_origin"]
            else:  # DESTINATION
                weight_used = load["net_dest"]
            freight = (weight_used / 1000) * load["rate"]

        # คำนวณค่าปรับ
        transit_loss = load["transit_loss"]
        max_loss_pct = (transit_loss_threshold_pct / 100) * load["net_origin"]
        max_allowed = min(max_loss_pct, transit_loss_threshold_kg)
        penalty = 0.0
        if transit_loss > max_allowed:
            excess_kg = transit_loss - max_allowed
            penalty = excess_kg * penalty_rate_per_kg
        net_pay = freight - penalty
        if net_pay < 0:
            net_pay = 0.0

        payment_details.append({
            "load": load,
            "freight": freight,
            "penalty": penalty,
            "net_pay": net_pay,
            "weight_used": weight_used if load["freight_mode"] == "PER_TON" else None
        })
        total_net_pay += net_pay

    st.subheader("💸 รายละเอียดการคำนวณค่าขนส่งและค่าปรับ")
    for i, detail in enumerate(payment_details):
        load = detail["load"]
        with st.expander(f"{load['load_id']} - {load['truck']} ({load['driver']})", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                if load["freight_mode"] == "FLAT_RATE":
                    st.write(f"**รูปแบบ:** เหมาเที่ยว")
                    st.write(f"**อัตรา:** {load['rate']:,.2f} บาท/เที่ยว")
                else:
                    st.write(f"**รูปแบบ:** บาทต่อตัน (ฐานน้ำหนัก: {'ต้นทาง' if load['base_weight_option']=='ORIGIN' else 'ปลายทาง'})")
                    st.write(f"**น้ำหนักที่ใช้:** {detail['weight_used']:,} kg ({detail['weight_used']/1000:.2f} ตัน)")
                    st.write(f"**อัตรา:** {load['rate']:,.2f} บาท/ตัน")
                st.write(f"**ค่าขนส่งก่อนหัก:** {detail['freight']:,.2f} บาท")
                st.write(f"**Transit Loss:** {load['transit_loss']} kg (เกณฑ์ยอมรับ {max_allowed:.0f} kg)")
                st.write(f"**ค่าปรับ:** {detail['penalty']:,.2f} บาท")
            with col2:
                st.write(f"**Impurity:** {load['impurity_kg']} kg")
                st.write(f"**หมายเหตุจากเคลียร์บิล:** {load['clearing_remark']}")
                st.metric("ค่าขนส่งสุทธิ (Net Pay)", f"{detail['net_pay']:,.2f} บาท")

            # อนุญาตให้เปลี่ยนฐานน้ำหนักย้อนหลัง (ถ้าเป็น PER_TON)
            if load["freight_mode"] == "PER_TON":
                new_base = st.radio(
                    "เปลี่ยนฐานน้ำหนักสำหรับเที่ยวนี้?",
                    ["ORIGIN", "DESTINATION"],
                    index=0 if load["base_weight_option"]=="ORIGIN" else 1,
                    key=f"base_{i}"
                )
                if new_base != load["base_weight_option"]:
                    st.warning("ฐานน้ำหนักถูกเปลี่ยน ระบบจะคำนวณใหม่เมื่อกดยืนยัน (ในของจริงจะรีเฟรช)")

    st.markdown("---")
    st.subheader("📦 สรุปยอดรวม")
    st.metric("รวมค่าขนส่งสุทธิที่ต้องจ่ายทั้งหมด", f"{total_net_pay:,.2f} บาท")

    # ฟอร์มบันทึกการจ่าย
    with st.form("payment_form"):
        st.write("**ข้อมูลการจ่าย**")
        payment_method = st.radio("วิธีจ่าย", ["เงินสด", "โอนธนาคาร"])
        bank_ref = ""
        if payment_method == "โอนธนาคาร":
            bank_ref = st.text_input("เลขที่อ้างอิงการโอน")
        paid_date = st.date_input("วันที่จ่าย", date.today())
        payment_remark = st.text_area("หมายเหตุการจ่าย (เพิ่มเติม)", value="")

        st.markdown("---")
        st.write("**ตัวอย่างก่อนบันทึก (Preview)**")
        st.write(f"จ่ายค่าขนส่ง {len(selected_loads)} เที่ยว รวม {total_net_pay:,.2f} บาท วันที่ {paid_date}")
        if payment_method == "โอนธนาคาร":
            st.write(f"โอนธนาคาร เลขอ้างอิง: {bank_ref}")

        submitted = st.form_submit_button("✅ ยืนยันการจ่าย")
        if submitted:
            # TODO: บันทึกข้อมูลลงตาราง freight_payments, อัปเดตสถานะเป็น PAID
            st.success("บันทึกการจ่ายค่าขนส่งเรียบร้อย!")
            st.balloons()

    # ปุ่มพิมพ์ใบสำคัญจ่าย
    if st.button("🖨️ พิมพ์ใบสำคัญจ่าย"):
        st.write("พิมพ์ใบสำคัญจ่าย (จำลอง)")
else:
    st.info("กรุณาเลือกอย่างน้อย 1 รายการเพื่อดำเนินการ")