import streamlit as st

st.header("⚙️ ตั้งค่าระบบ (มีผลกับทั้งระบบ)")

with st.form("settings_form"):
    st.subheader("เกณฑ์น้ำหนักขาด (Transit Loss)")
    transit_pct = st.number_input(
        "เกณฑ์ % ของน้ำหนักต้นทางที่ยอมรับได้",
        min_value=0.0, max_value=10.0, step=0.1,
        value=st.session_state.transit_loss_pct
    )
    transit_kg = st.number_input(
        "เกณฑ์น้ำหนักขาดสูงสุด (กก.) ที่ยอมรับได้",
        min_value=0, step=1,
        value=st.session_state.transit_loss_kg
    )

    st.subheader("อัตราค่าปรับน้ำหนักเกินเกณฑ์")
    penalty_rate = st.number_input(
        "ค่าปรับต่อกิโลกรัม (บาท) สำหรับน้ำหนักที่เกินเกณฑ์",
        min_value=0.0, step=1.0,
        value=st.session_state.penalty_rate_per_kg,
        help="ตั้งให้สูงมากหากยังไม่ต้องการหัก (เช่น 9999 บาท/กก.)"
    )

    st.subheader("อัตราค่าขนส่งเริ่มต้น")
    flat_rate = st.number_input(
        "เหมาเที่ยว (บาท/เที่ยว)",
        min_value=0.0, step=100.0,
        value=st.session_state.freight_flat_rate
    )
    per_ton_rate = st.number_input(
        "ต่อตัน (บาท/ตัน)",
        min_value=0.0, step=10.0,
        value=st.session_state.freight_per_ton_rate
    )
    base_weight = st.radio(
        "ฐานน้ำหนักเริ่มต้นสำหรับการคิดค่าขนส่งแบบต่อตัน",
        ["ต้นทาง", "ปลายทาง"],
        index=0 if st.session_state.default_base_weight == "ต้นทาง" else 1
    )

    submitted = st.form_submit_button("💾 บันทึกการตั้งค่า")
    if submitted:
        st.session_state.transit_loss_pct = transit_pct
        st.session_state.transit_loss_kg = transit_kg
        st.session_state.penalty_rate_per_kg = penalty_rate
        st.session_state.freight_flat_rate = flat_rate
        st.session_state.freight_per_ton_rate = per_ton_rate
        st.session_state.default_base_weight = base_weight
        st.success("บันทึกการตั้งค่าเรียบร้อย! (มีผลทันที)")
        st.balloons()