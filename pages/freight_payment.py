import streamlit as st
import pandas as pd
from datetime import date, datetime

st.header("🚛 จ่ายค่าขนส่งให้สิบล้อ (Freight Payment)")

# ---- ดึงค่าจาก settings ----
pct_threshold = st.session_state.get("transit_loss_pct", 0.5)
kg_threshold = st.session_state.get("transit_loss_kg", 50)
penalty_rate = st.session_state.get("penalty_rate_per_kg", 10.0)
flat_rate_default = st.session_state.get("freight_flat_rate", 3000.0)
per_ton_rate_default = st.session_state.get("freight_per_ton_rate", 100.0)

# ---- ข้อมูลโหลดจำลอง (เฉพาะที่ยัง UNPAID) ----
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
            "clearing_remark": "ฝนตก",
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

# ---- ประวัติการจ่าย (ถ้ายังไม่มี) ----
if "freight_payment_history" not in st.session_state:
    st.session_state.freight_payment_history = []

# ---- ดึงเฉพาะรายการที่ยัง UNPAID ----
unpaid_loads = [l for l in st.session_state.freight_demo_loads if l["status"] == "UNPAID"]

st.subheader("📋 รายการที่ยังไม่ได้จ่าย")
if not unpaid_loads:
    st.success("ไม่มีรายการค้างจ่าย")
else:
    df = pd.DataFrame([{
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
    } for l in unpaid_loads])
    st.dataframe(df, use_container_width=True)

    selected_ids = st.multiselect("เลือก Load Order ที่ต้องการจ่าย", [l["load_id"] for l in unpaid_loads])

    if selected_ids:
        selected_loads = [l for l in unpaid_loads if l["load_id"] in selected_ids]

        # เก็บอัตราที่แก้ไข
        if "edited_rates" not in st.session_state:
            st.session_state.edited_rates = {}
        for load in selected_loads:
            if load["load_id"] not in st.session_state.edited_rates:
                st.session_state.edited_rates[load["load_id"]] = load["rate"]

        payment_details = []
        total_net_pay = 0.0

        for load in selected_loads:
            current_rate = st.session_state.edited_rates[load["load_id"]]
            if load["freight_mode"] == "FLAT_RATE":
                freight = current_rate
                weight_used = None
            else:
                weight_used = load["net_origin"] if load["base_weight_option"] == "ORIGIN" else load["net_dest"]
                freight = (weight_used / 1000) * current_rate

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
                "weight_used": weight_used
            })
            total_net_pay += net_pay

        st.subheader("💸 รายละเอียดการคำนวณ (แก้ไขอัตราได้)")
        for i, detail in enumerate(payment_details):
            load = detail["load"]
            with st.expander(f"{load['load_id']} - {load['truck']} ({load['driver']})", expanded=True):
                if load["freight_mode"] == "FLAT_RATE":
                    new_rate = st.number_input("อัตราเหมา (บาท/เที่ยว)", min_value=0.0, step=100.0, value=detail["current_rate"], key=f"rate_{load['load_id']}")
                else:
                    new_rate = st.number_input("อัตราค่าขนส่ง (บาท/ตัน)", min_value=0.0, step=10.0, value=detail["current_rate"], key=f"rate_{load['load_id']}")
                if new_rate != detail["current_rate"]:
                    st.session_state.edited_rates[load["load_id"]] = new_rate

                if load["freight_mode"] == "PER_TON":
                    current_base = load["base_weight_option"]
                    new_base = st.radio("ฐานน้ำหนัก", ["ORIGIN", "DESTINATION"], index=0 if current_base=="ORIGIN" else 1, key=f"base_{load['load_id']}")
                    if new_base != current_base:
                        load["base_weight_option"] = new_base
                        # อัปเดตในรายการหลัก
                        for d in st.session_state.freight_demo_loads:
                            if d["load_id"] == load["load_id"]:
                                d["base_weight_option"] = new_base

                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**ค่าขนส่งก่อนหัก:** {detail['freight']:,.2f} บาท")
                    if load["freight_mode"] == "PER_TON":
                        st.write(f"**น้ำหนักที่ใช้:** {detail['weight_used']:,} kg")
                    st.write(f"**Transit Loss:** {load['transit_loss']} kg (เกณฑ์ {max_allowed:.0f} kg)")
                    st.write(f"**ค่าปรับ:** {detail['penalty']:,.2f} บาท")
                with col2:
                    st.write(f"**Impurity:** {load['impurity_kg']} kg")
                    st.write(f"**หมายเหตุเคลียร์:** {load['clearing_remark']}")
                    st.metric("ค่าขนส่งสุทธิ", f"{detail['net_pay']:,.2f} บาท")

        st.markdown("---")
        st.metric("รวมค่าขนส่งสุทธิที่ต้องจ่ายทั้งหมด", f"{total_net_pay:,.2f} บาท")

        with st.form("payment_form"):
            payment_method = st.radio("วิธีจ่าย", ["เงินสด", "โอนธนาคาร"])
            bank_ref = ""
            if payment_method == "โอนธนาคาร":
                bank_ref = st.text_input("เลขที่อ้างอิงการโอน")
            paid_date = st.date_input("วันที่จ่าย", date.today())
            payment_remark = st.text_area("หมายเหตุการจ่าย (ถ้ามี)")

            st.write(f"**สรุป:** จ่ายค่าขนส่ง {len(selected_loads)} เที่ยว รวม {total_net_pay:,.2f} บาท")

            submitted = st.form_submit_button("✅ ยืนยันการจ่าย")
            if submitted:
                # เปลี่ยนสถานะเป็น PAID ในรายการหลัก
                for load in selected_loads:
                    for d in st.session_state.freight_demo_loads:
                        if d["load_id"] == load["load_id"]:
                            d["status"] = "PAID"
                            break
                # บันทึกประวัติ
                record = {
                    "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "load_ids": [l["load_id"] for l in selected_loads],
                    "trucks": [l["truck"] for l in selected_loads],
                    "total_amount": total_net_pay,
                    "method": payment_method,
                    "ref": bank_ref,
                    "paid_date": str(paid_date),
                    "remark": payment_remark
                }
                st.session_state.freight_payment_history.append(record)
                # ล้างอัตราที่แก้ไข (เฉพาะที่เลือก)
                for load in selected_loads:
                    if load["load_id"] in st.session_state.edited_rates:
                        del st.session_state.edited_rates[load["load_id"]]
                st.success("บันทึกการจ่ายค่าขนส่งเรียบร้อย!")
                st.balloons()
                st.rerun()

# ---- แสดงประวัติการจ่าย (ถ้ามี) ----
if st.session_state.freight_payment_history:
    st.markdown("---")
    st.subheader("📜 ประวัติการจ่ายค่าขนส่ง")
    history_df = pd.DataFrame(st.session_state.freight_payment_history)
    st.dataframe(history_df, use_container_width=True)