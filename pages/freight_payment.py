import streamlit as st
import pandas as pd
from datetime import date

st.header("🚛 จ่ายค่าขนส่งให้สิบล้อ (Freight Payment)")

# ---- ดึงค่าจาก settings ----
pct_threshold = st.session_state.get("transit_loss_pct", 0.5)
kg_threshold = st.session_state.get("transit_loss_kg", 50)
penalty_rate = st.session_state.get("penalty_rate_per_kg", 10.0)
flat_rate_default = st.session_state.get("freight_flat_rate", 3000.0)
per_ton_rate_default = st.session_state.get("freight_per_ton_rate", 100.0)

# ---- ข้อมูลโหลดจำลอง (ภายหลังดึงจาก Supabase) ----
if "freight_demo_loads" not in st.session_state:
    st.session_state.freight_demo_loads = [
        {
            "load_id": "LO0001",
            "truck": "80-1234",
            "driver": "สมชาย",
            "company": "สมชายขนส่ง",
            "freight_mode": "FLAT_RATE",
            "rate": flat_rate_default,
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
            "rate": per_ton_rate_default,
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
            "rate": per_ton_rate_default,
            "base_weight_option": "DESTINATION",
            "net_origin": 14000,
            "net_dest": 13800,
            "transit_loss": 200,
            "impurity_kg": 0,
            "clearing_remark": "ไม่มี",
            "status": "UNPAID"
        }
    ]

demo_loads = st.session_state.freight_demo_loads

# ---- สร้างตารางสรุป ----
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

# ---- เลือกรายการที่ต้องการจ่าย ----
selected_ids = st.multiselect(
    "เลือก Load Order ที่ต้องการจ่าย (สามารถจ่ายหลายเที่ยวพร้อมกัน)",
    [l["load_id"] for l in demo_loads]
)

if selected_ids:
    selected_loads = [l for l in demo_loads if l["load_id"] in selected_ids]

    # ---- คำนวณ (ใช้ rate ที่อาจถูกแก้ไข) ----
    payment_details = []
    total_net_pay = 0.0

    # เก็บอัตราที่แก้ไขใน session_state (key = load_id)
    if "edited_rates" not in st.session_state:
        st.session_state.edited_rates = {}

    for load in selected_loads:
        # กำหนดค่าเริ่มต้นของ rate ที่แก้ไขได้
        if load["load_id"] not in st.session_state.edited_rates:
            st.session_state.edited_rates[load["load_id"]] = load["rate"]

        current_rate = st.session_state.edited_rates[load["load_id"]]

        # คำนวณค่าขนส่ง
        if load["freight_mode"] == "FLAT_RATE":
            freight = current_rate
            weight_used = None
        else:
            # ใช้ base_weight_option ที่อาจเปลี่ยนได้ (เหมือนเดิม)
            if load["base_weight_option"] == "ORIGIN":
                weight_used = load["net_origin"]
            else:
                weight_used = load["net_dest"]
            freight = (weight_used / 1000) * current_rate

        # คำนวณค่าปรับ
        transit_loss = load["transit_loss"]
        max_loss_pct = (pct_threshold / 100) * load["net_origin"]
        max_allowed = min(max_loss_pct, kg_threshold)
        penalty = 0.0
        if transit_loss > max_allowed:
            excess_kg = transit_loss - max_allowed
            penalty = excess_kg * penalty_rate
        net_pay = max(freight - penalty, 0.0)

        payment_details.append({
            "load": load,
            "current_rate": current_rate,
            "freight": freight,
            "penalty": penalty,
            "net_pay": net_pay,
            "weight_used": weight_used if load["freight_mode"] == "PER_TON" else None
        })
        total_net_pay += net_pay

    # ---- UI สำหรับแต่ละเที่ยว ----
    st.subheader("💸 รายละเอียดการคำนวณ (สามารถแก้ไขอัตราค่าขนส่งได้)")

    for i, detail in enumerate(payment_details):
        load = detail["load"]
        with st.expander(f"{load['load_id']} - {load['truck']} ({load['driver']})", expanded=True):
            # --- แก้ไขอัตราค่าขนส่ง ---
            if load["freight_mode"] == "FLAT_RATE":
                new_rate = st.number_input(
                    "🚛 อัตราเหมา (บาท/เที่ยว)",
                    min_value=0.0, step=100.0,
                    value=detail["current_rate"],
                    key=f"rate_{load['load_id']}"
                )
            else:
                new_rate = st.number_input(
                    "🚛 อัตราค่าขนส่ง (บาท/ตัน)",
                    min_value=0.0, step=10.0,
                    value=detail["current_rate"],
                    key=f"rate_{load['load_id']}"
                )
            # อัปเดตค่า rate ใน session_state
            if new_rate != detail["current_rate"]:
                st.session_state.edited_rates[load["load_id"]] = new_rate
                # จะเกิดการ rerun อัตโนมัติเมื่อเปลี่ยนค่าใน number_input

            # --- เปลี่ยนฐานน้ำหนัก (กรณี per ton) ---
            if load["freight_mode"] == "PER_TON":
                current_base = load["base_weight_option"]
                new_base = st.radio(
                    "ฐานน้ำหนักที่ใช้คิด",
                    ["ORIGIN", "DESTINATION"],
                    index=0 if current_base == "ORIGIN" else 1,
                    key=f"base_{load['load_id']}"
                )
                if new_base != current_base:
                    load["base_weight_option"] = new_base
                    # อัปเดตใน demo_loads เพื่อให้คำนวณใหม่เมื่อ rerun
                    for d in st.session_state.freight_demo_loads:
                        if d["load_id"] == load["load_id"]:
                            d["base_weight_option"] = new_base
                    # rerun จะเกิดจาก radio เปลี่ยนเอง

            # --- แสดงผลการคำนวณใหม่ ---
            col1, col2 = st.columns(2)
            with col1:
                if load["freight_mode"] == "FLAT_RATE":
                    st.write(f"**ค่าขนส่งก่อนหัก:** {detail['freight']:,.2f} บาท")
                else:
                    st.write(f"**น้ำหนักที่ใช้:** {detail['weight_used']:,} kg ({detail['weight_used']/1000:.2f} ตัน)")
                    st.write(f"**ค่าขนส่งก่อนหัก:** {detail['freight']:,.2f} บาท")
                st.write(f"**Transit Loss:** {load['transit_loss']} kg")
                st.write(f"**เกณฑ์ยอมรับ:** สูงสุด {max_allowed:.0f} kg")
                st.write(f"**ค่าปรับ:** {detail['penalty']:,.2f} บาท")
            with col2:
                st.write(f"**Impurity:** {load['impurity_kg']} kg")
                st.write(f"**หมายเหตุจากเคลียร์บิล:** {load['clearing_remark']}")
                st.metric("ค่าขนส่งสุทธิ (Net Pay)", f"{detail['net_pay']:,.2f} บาท")

    # ---- สรุปยอดรวมและแบบฟอร์มจ่าย ----
    st.markdown("---")
    st.subheader("📦 สรุปยอดรวม")
    st.metric("รวมค่าขนส่งสุทธิที่ต้องจ่ายทั้งหมด", f"{total_net_pay:,.2f} บาท")

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
            # TODO: บันทึก freight_payments พร้อม rate ที่แก้ไขแล้ว
            for detail in payment_details:
                # ใช้ detail["current_rate"] (แก้ไขแล้ว) ในการบันทึก
                pass
            st.success("บันทึกการจ่ายค่าขนส่งเรียบร้อย!")
            st.balloons()
            # เคลียร์สถานะเพื่อเริ่มใหม่ (ถ้าต้องการ)
            # st.session_state.edited_rates = {}
            # st.rerun()

    if st.button("🖨️ พิมพ์ใบสำคัญจ่าย"):
        st.write("พิมพ์ใบสำคัญจ่าย (จำลอง)")
else:
    st.info("กรุณาเลือกอย่างน้อย 1 รายการเพื่อดำเนินการ")