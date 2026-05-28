import streamlit as st

st.header("📦 สต็อกคงเหลือ (Physical / Reporting)")

st.markdown("---")

# จำลองยอดสต็อก (ภายหลังดึงจาก inventory_transactions)
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Physical Stock", value="1,250,000 kg")
with col2:
    st.metric(label="Reporting Stock", value="980,000 kg")

st.markdown("---")
st.subheader("รายละเอียดสต็อกแยกตามเกรด (ตัวอย่าง)")

detail_data = [
    {"ประเภท": "เหล็กเกรด A", "Physical (kg)": 800000, "Reporting (kg)": 600000},
    {"ประเภท": "เหล็กเกรด B", "Physical (kg)": 300000, "Reporting (kg)": 250000},
    {"ประเภท": "เศษเหล็กผสม", "Physical (kg)": 150000, "Reporting (kg)": 130000},
]
st.table(detail_data)

st.info("ในอนาคตจะแสดงกราฟแท่งและ FIFO Layers ที่นี่")