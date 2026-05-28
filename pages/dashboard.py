import streamlit as st

st.header("📊 แดชบอร์ดผู้บริหาร")

col1, col2, col3 = st.columns(3)
col1.metric("กำไรวันนี้", "35,000 บาท")
col2.metric("เที่ยวรถวันนี้", 8)
col3.metric("สต็อกคงเหลือ", "1.2 ล้าน กก.")

st.markdown("---")
st.subheader("แนวโน้มกำไร 7 วัน")
st.line_chart([12000, 15000, 18000, 13000, 22000, 19000, 35000])

st.subheader("น้ำหนักขาดระหว่างขนส่ง (กก.)")
st.bar_chart({"Transit Loss": [120, 80, 150, 90, 60]})