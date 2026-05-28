import streamlit as st
import pandas as pd
from datetime import date, timedelta

# =====================================================
# 🛢️ ข้อมูลจำลอง (ภายหลังเชื่อม Supabase)
# =====================================================
if "purchase_orders" not in st.session_state:
    # ตัวอย่าง Purchase Orders
    st.session_state.purchase_orders = [
        {
            "id": "P0001",
            "purchase_date": date(2026, 5, 27),
            "created_by": "เสมียน",
            "lines": [
                {"product": "เหล็กเกรด A", "phys_weight": 1000, "phys_price": 8.5, "rep_weight": 950, "rep_price": 9.0},
                {"product": "เหล็กเกรด B", "phys_weight": 520, "phys_price": 8.0, "rep_weight": 500, "rep_price": 8.5}
            ]
        },
        {
            "id": "P0002",
            "purchase_date": date(2026, 5, 20),
            "created_by": "เสมียน",
            "lines": [
                {"product": "เศษเหล็กผสม", "phys_weight": 800, "phys_price": 7.0, "rep_weight": 800, "rep_price": 7.0}
            ]
        }
    ]

if "purchase_edit_logs" not in st.session_state:
    st.session_state.purchase_edit_logs = []  # เก็บ log การแก้ไข

# =====================================================
# 🎨 ฟังก์ชันแสดงผลแยกสีใน DataFrame
# =====================================================
def styled_orders_df(orders):
    rows = []
    for po in orders:
        total_phys = sum(l["phys_weight"] for l in po["lines"])
        total_rep = sum(l["rep_weight"] for l in po["lines"])
        rows.append({
            "เลขที่บิล": po["id"],
            "วันที่": po["purchase_date"].strftime("%Y-%m-%d"),
            "🔴 Physical (kg)": total_phys,
            "🔵 Reporting (kg)": total_rep,
            "รายการ": len(po["lines"]),
            "ผู้บันทึก": po["created_by"]
        })
    df = pd.DataFrame(rows)
    return df

# =====================================================
# 🧾 หน้าประวัติการซื้อ
# =====================================================
st.header("📋 ประวัติการซื้อ")
st.info("🔴 Physical | 🔵 Reporting")

# ---- ตัวกรอง ----
col1, col2 = st.columns(2)
with col1:
    date_from = st.date_input("จากวันที่", date.today() - timedelta(days=30))
with col2:
    date_to = st.date_input("ถึงวันที่", date.today())

# กรองตามวันที่
filtered_orders = [
    po for po in st.session_state.purchase_orders
    if date_from <= po["purchase_date"] <= date_to
]

# แสดงตารางสรุป
st.subheader("รายการใบซื้อ")
df = styled_orders_df(filtered_orders)
st.dataframe(df, use_container_width=True, hide_index=True)

# ---- ปุ่มดูรายละเอียด / แก้ไข ----
st.markdown("---")
st.subheader("🔍 เลือกใบซื้อเพื่อดูรายละเอียด / แก้ไข")

if not filtered_orders:
    st.warning("ไม่มีข้อมูลในช่วงวันที่นี้")
else:
    selected_id = st.selectbox(
        "เลือกเลขที่บิล",
        [po["id"] for po in filtered_orders]
    )

    selected_order = next(po for po in filtered_orders if po["id"] == selected_id)

    # ---- แสดงรายละเอียดแบบแยกสี ----
    st.write(f"**วันที่ซื้อ:** {selected_order['purchase_date'].strftime('%Y-%m-%d')}  |  ผู้บันทึก: {selected_order['created_by']}")
    lines_df = pd.DataFrame([
        {
            "ประเภท": l["product"],
            "🔴 Phys (kg)": l["phys_weight"],
            "🔴 ราคา/ตัน": f"{l['phys_price']:,.2f}",
            "🔵 Rep (kg)": l["rep_weight"],
            "🔵 ราคา/ตัน": f"{l['rep_price']:,.2f}"
        } for l in selected_order["lines"]
    ])
    st.dataframe(lines_df, use_container_width=True, hide_index=True)

    total_phys = sum(l["phys_weight"] for l in selected_order["lines"])
    total_rep = sum(l["rep_weight"] for l in selected_order["lines"])
    st.markdown(f"**รวม 🔴 Physical:** {total_phys:,} kg  |  **🔵 Reporting:** {total_rep:,} kg")

    # ---- เงื่อนไขการแก้ไข ----
    days_ago = (date.today() - selected_order["purchase_date"]).days
    can_edit = False
    if days_ago <= 7:
        can_edit = True  # ทุกคน
    else:
        if st.session_state.role in ["manager", "owner"]:
            can_edit = True
        else:
            st.warning(f"เกิน 7 วัน ({days_ago} วัน) ต้องเป็นผู้จัดการหรือเจ้าของเท่านั้นที่แก้ไขได้")

    # ---- ปุ่มแก้ไข ----
    if can_edit:
        if st.button("✏️ แก้ไขใบซื้อนี้"):
            st.session_state.edit_mode = selected_id
            st.rerun()

    # ---- กระบวนการแก้ไข ----
    if "edit_mode" in st.session_state and st.session_state.edit_mode == selected_id:
        st.markdown("---")
        st.subheader("✏️ แก้ไขรายการสินค้า")
        with st.form("edit_form"):
            edited_lines = []
            for i, line in enumerate(selected_order["lines"]):
                st.write(f"**รายการที่ {i+1}: {line['product']}**")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    new_phys_w = st.number_input("🔴 Phys (kg)", min_value=0, step=100, value=line["phys_weight"], key=f"epw_{i}")
                with col2:
                    new_phys_p = st.number_input("🔴 ราคา/ตัน", min_value=0.0, step=0.5, value=line["phys_price"], key=f"epp_{i}")
                with col3:
                    new_rep_w = st.number_input("🔵 Rep (kg)", min_value=0, step=100, value=line["rep_weight"], key=f"erw_{i}")
                with col4:
                    new_rep_p = st.number_input("🔵 ราคา/ตัน", min_value=0.0, step=0.5, value=line["rep_price"], key=f"erp_{i}")
                edited_lines.append({
                    "product": line["product"],
                    "phys_weight": new_phys_w,
                    "phys_price": new_phys_p,
                    "rep_weight": new_rep_w,
                    "rep_price": new_rep_p
                })

            st.markdown("---")
            if st.form_submit_button("💾 บันทึกการแก้ไข"):
                # บันทึก Audit Log
                old_data = selected_order["lines"].copy()
                st.session_state.purchase_edit_logs.append({
                    "order_id": selected_id,
                    "edited_by": st.session_state.user["display_name"],
                    "edited_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "changes": f"แก้ไข {len(old_data)} รายการ (ดูรายละเอียดในระบบ)"
                })
                # อัปเดตข้อมูล
                selected_order["lines"] = edited_lines
                # เคลียร์สถานะแก้ไข
                del st.session_state.edit_mode
                st.success("บันทึกการแก้ไขเรียบร้อย (มีการบันทึก Audit Log)")
                st.balloons()
                st.rerun()

        if st.button("ยกเลิกการแก้ไข"):
            del st.session_state.edit_mode
            st.rerun()

# ---- ดู Audit Log (สำหรับ Manager/Owner) ----
if st.session_state.role in ["manager", "owner"]:
    st.markdown("---")
    st.subheader("📝 ประวัติการแก้ไข (Audit Log)")
    if st.session_state.purchase_edit_logs:
        log_df = pd.DataFrame(st.session_state.purchase_edit_logs)
        st.dataframe(log_df, use_container_width=True, hide_index=True)
    else:
        st.write("ยังไม่มีการแก้ไข")

# ---- พิมพ์ซ้ำ ----
st.markdown("---")
if st.button("🖨️ พิมพ์สลิปสรุปการซื้อ (จากรายการที่เลือก)"):
    st.write(f"พิมพ์สลิปสำหรับ {selected_id} (จำลอง)")