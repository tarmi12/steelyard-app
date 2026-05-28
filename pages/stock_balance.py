import streamlit as st
st.header("📦 สต็อกคงเหลือ (Physical / Reporting)")
col1, col2 = st.columns(2)
col1.metric("Physical", "1,250,000 kg")
col2.metric("Reporting", "980,000 kg")