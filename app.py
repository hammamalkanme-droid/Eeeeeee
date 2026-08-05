import streamlit as st
import pandas as pd

st.set_page_config(page_title="منظومة فريق النخبة", layout="wide")

st.markdown("<h1 style='text-align: right;'>🌐 لوحة تحكم فريق النخبة</h1>", unsafe_allow_html=True)
st.markdown("---")

# بيانات تجريبية سريعة تضمن اشتغال الصفحة فوراً
if 'tasks' not in st.session_state:
    st.session_state.tasks = pd.DataFrame({
        "المشروع": ["بوتات زيد", "مشروع فضاء", "مناهل العلم"],
        "المهمة": ["رفع الملخصات", "متابعة الجدول", "إعداد الامتحانات"],
        "المسؤول": ["سفيان اليونسي", "احميدة جمال", "عبد القادر مجيد"],
        "الحالة": ["قيد العمل", "مستمر", "لم يبدأ"]
    })

# القائمة الجانبية لتسجيل الدخول
st.sidebar.header("تسجيل الدخول")
user = st.sidebar.selectbox("اختر اسمك:", ["همَّام الكانمي (المدير)", "سفيان اليونسي", "عبد القادر مجيد", "احميدة جمال"])

st.sidebar.success(f"مرحباً بك: {user}")

# عرض المهام
st.subheader("📋 جدول المهام والعمليات")
st.dataframe(st.session_state.tasks, use_container_width=True)

# إضافة مهمة جديدة
st.subheader("➕ إضافة مهمة جديدة")
with st.form("new_task_form"):
    p_name = st.selectbox("المشروع", ["بوتات زيد", "مشروع فضاء", "مناهل العلم", "الندوات والفعاليات"])
    t_title = st.text_input("عنوان المهمة")
    t_assignee = st.text_input("المسؤول عنها")
    submitted = st.form_submit_button("حفظ المهمة")
    
    if submitted and t_title:
        new_row = pd.DataFrame({"المشروع": [p_name], "المهمة": [t_title], "المسؤول": [t_assignee], "الحالة": ["قيد العمل"]})
        st.session_state.tasks = pd.concat([st.session_state.tasks, new_row], ignore_index=True)
        st.success("✅ تم إضافة المهمة بنجاح! دير تحديث للصفحة باش تشوفها.")
