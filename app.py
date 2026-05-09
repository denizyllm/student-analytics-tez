import streamlit as st
import pandas as pd
import json
import os
import matplotlib.pyplot as plt
import seaborn as sns
from groq import Groq 

from sklearn.linear_model import LinearRegression


st.set_page_config(page_title="Student Analytics Platform", layout="wide")


DB_FILE = "student_analytics_db.json"

def save_data():
    current_user = st.session_state.get('current_user', 'default')
    db_data = {}
    
    
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            try:
                db_data = json.load(f)
            except:
                pass
    
    
    db_data[current_user] = {
        'classes': st.session_state.get('classes', {}),
        'students': st.session_state.get('students', {})
    }
    
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db_data, f, ensure_ascii=False, indent=4)

def load_data():
    current_user = st.session_state.get('current_user', 'default')
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            try:
                db_data = json.load(f)
                
                user_data = db_data.get(current_user, {})
                st.session_state['classes'] = user_data.get('classes', {})
                st.session_state['students'] = user_data.get('students', {})
            except:
                st.session_state['classes'], st.session_state['students'] = {}, {}
    else:
        st.session_state['classes'], st.session_state['students'] = {}, {}

def train_ai_model():
    try:
        ref_path = "data/student_data.csv"
        if os.path.exists(ref_path):
            df = pd.read_csv(ref_path)
            
            for col in ['G1', 'G2', 'G3', 'absences']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
            df = df.dropna(subset=['G1', 'G2', 'G3', 'absences'])

            for col in ['G1', 'G2', 'G3']:
                df[col] = df[col] * 5
            
            df['G_Avg'] = (df['G1'] + df['G2']) / 2 
            X = df[['G_Avg', 'absences']]
            y = df['G3']
            
            model = LinearRegression()
            model.fit(X, y)
            return model
    except Exception as e:
        st.error(f"AI Model Error: {e}")
    return None


def generate_warning_email(api_key, student_name, issue_type, details):
    if not api_key:
        return "⚠️ Error: Please enter your Groq API Key in the sidebar first!"
    try:
        client = Groq(api_key=api_key)
        
        if issue_type == "attendance":
            prompt = f"Write a polite, professional, and serious academic warning email to a university student named {student_name}. They are critically close to failing the course due to absences. They currently have {details['absences']} absences and the maximum limit is {details['limit']}. Warn them that exceeding this limit will result in automatic failure. Keep it under 150 words."
        elif issue_type == "grade":
            prompt = f"Write a supportive but urgent academic warning email to a university student named {student_name}. Based on their midterm scores and AI predictions, their projected final Total Score is {details['projected_score']} which is below the passing grade of 40. Encourage them to study hard for the final exam. Keep it professional, encouraging, and under 150 words."
            
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.4, 
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"API Connection Error: {str(e)}"

if 'ml_model' not in st.session_state:
    st.session_state['ml_model'] = train_ai_model()


if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False


if st.session_state['logged_in']:
    if 'classes' not in st.session_state or 'students' not in st.session_state:
        load_data()


if not st.session_state['logged_in']:
    st.write("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown(
            """
            <h1 style='text-align: center; color: #1A365D;'>Welcome to Student Analytics</h1>
            <p style='text-align: center; color: #7f8c8d;'>Please sign in to access your dashboard.</p>
            """, 
            unsafe_allow_html=True
        )
        with st.container():
            u = st.text_input("Username / Email", placeholder="e.g. melih.cinar@yildiz.edu.tr")
            p = st.text_input("Password", type="password", placeholder="••••••••")
            st.write("<br>", unsafe_allow_html=True)
            
            if st.button("Secure Login", use_container_width=True):
                if (u == "melih.cinar@yildiz.edu.tr" and p == "tez2026") or (u == "deniz.admin" and p == "admin123"):
                    st.session_state['logged_in'] = True
                    st.session_state['current_user'] = u
                    load_data() 
                    st.rerun()
                else:
                    st.error("Oops! Incorrect username or password. Please try again. ")

else:
    c1, c2 = st.columns([9, 1])
    with c1:
        st.title("🎓 Student Performance Analytics")
        st.success(f"Welcome, {st.session_state['current_user']}!")
    with c2:
        if st.button("Log Out"):
            st.session_state['logged_in'] = False
            
            if 'classes' in st.session_state: del st.session_state['classes']
            if 'students' in st.session_state: del st.session_state['students']
            if 'current_user' in st.session_state: del st.session_state['current_user']
            st.rerun()

    
    st.sidebar.header("📚 Class Management")
    
    with st.sidebar.expander("➕ Create New Class", expanded=False):
        c_name = st.text_input("Class Name")
        c_days = st.number_input("Days per Week", 1, 5, 1)
        c_limit = st.slider("Required Attendance (%)", 0, 100, 70)
        c_w1 = st.slider("Initial G1 Weight %", 0, 100, 30)
        c_w2 = st.slider("Initial G2 Weight %", 0, 100, 30)
        if st.button("Confirm Creation"):
            if c_name:
                st.session_state['classes'][c_name] = {
                    "days_per_week": c_days, 
                    "req_attendance": c_limit, 
                    "total_sessions": c_days * 12,
                    "w1": c_w1,
                    "w2": c_w2
                }
                st.session_state['students'][c_name] = []
                save_data()
                st.rerun()

    class_list = list(st.session_state['classes'].keys())
    active_class = st.sidebar.selectbox("Select Active Class", class_list) if class_list else None
    
    if active_class:
        with st.sidebar.expander("🗑️ Delete Current Class", expanded=False):
            st.warning(f"This will permanently delete {active_class}.")
            if st.button(f"Confirm Delete"):
                del st.session_state['classes'][active_class]
                if active_class in st.session_state['students']: del st.session_state['students'][active_class]
                save_data()
                st.rerun()

    current_week = st.sidebar.select_slider("📅 System Week", options=list(range(1, 17)), value=1)

    if active_class:
        ci = st.session_state['classes'][active_class]
        st.sidebar.divider()
        st.sidebar.markdown(f"### ⚖️ {active_class} Grade Weights")
        
        new_w1 = st.sidebar.slider("Midterm 1 (G1) %", 0, 100, ci.get('w1', 30))
        new_w2 = st.sidebar.slider("Midterm 2 (G2) %", 0, 100, ci.get('w2', 30))
        new_w3 = 100 - (new_w1 + new_w2)
        st.sidebar.info(f"Final (G3) Weight: %{new_w3}")
        
        if new_w1 != ci.get('w1', 30) or new_w2 != ci.get('w2', 30):
            st.session_state['classes'][active_class]['w1'] = new_w1
            st.session_state['classes'][active_class]['w2'] = new_w2
            save_data()
            
        w1, w2, w3 = new_w1, new_w2, new_w3
    
    st.sidebar.divider()
    st.sidebar.markdown("### 🤖 Groq LLM Setup")
    groq_api_key = st.sidebar.text_input("Groq API Key", type="password", placeholder="gsk_..")
    if not groq_api_key:
        st.sidebar.caption("Enter API key to enable Smart Email Generation.")

    if active_class:
        st.sidebar.divider()
        with st.sidebar.expander("👤 Add New Student", expanded=False):
            with st.form("std_form", clear_on_submit=True):
                s_name = st.text_input("Full Name")
                s_id = st.text_input("Student ID")
                s_abs = st.number_input("Absences (Days)", 0, 30, 0)
                s_g1 = st.number_input("G1 Note", 0, 100, 0)
                if st.form_submit_button("Save Student"):
                    if s_name and s_id:
                        st.session_state['students'][active_class].append({"ID": s_id, "Name": s_name, "Absences": s_abs, "G1": s_g1, "G2": 0, "G3": 0})
                        save_data()
                        st.rerun()
        
        current_students = st.session_state['students'].get(active_class, [])
        if current_students:
            with st.sidebar.expander("❌ Remove Student", expanded=False):
                student_names = [s['Name'] for s in current_students]
                student_to_remove = st.selectbox("Select Student to Delete", student_names)
                if st.button("Delete Selected Student", use_container_width=True):
                    st.session_state['students'][active_class] = [s for s in current_students if s['Name'] != student_to_remove]
                    save_data()
                    st.rerun()

    
    tab1, tab2, tab3 = st.tabs(["📊 Class Dashboard", "🔍 Individual Analysis", "📑 Reference Data"])

    with tab1:
        if active_class:
            ci = st.session_state['classes'][active_class]
            st.subheader(f"Dashboard: {active_class} (Week {current_week})")
            
            atnd_val = f"%{ci['req_attendance']}" if ci['req_attendance'] > 0 else "None"
            st.info(f"Attendance Policy: **{atnd_val}** | Capacity: **{ci['total_sessions']} Total Days**")
            
            if current_week == 8: st.warning("📢 Week 8: Midterm 1 Exams in progress!")
            if current_week == 12: st.warning("📢 Week 12: Midterm 2 / Project Submission Deadline!")
            if current_week >= 15: st.error("📢 Finals Week! Final grade entry required.")

            students = st.session_state['students'].get(active_class, [])
            if students:
                df = pd.DataFrame(students)
                
                df['Total Score'] = (df['G1']*(w1/100)) + (df['G2']*(w2/100)) + (df['G3']*(w3/100))
                
                def get_ai_prediction(row):
                    model = st.session_state.get('ml_model')
                    if model and row['G1'] > 0:
                        g2_val = row['G2'] if row['G2'] > 0 else row['G1']
                        current_avg = (row['G1'] + g2_val) / 2
                        features = [[current_avg, row['Absences']]]
                        prediction = model.predict(features)[0]
                        return round(max(0, min(100, prediction)), 1)
                    return None

                df['AI Final Prediction'] = df.apply(get_ai_prediction, axis=1)
                
                limit = ci['total_sessions'] * (1 - ci['req_attendance']/100)
                
                def get_status(row):
                    if ci['req_attendance'] > 0:
                        
                        if row['Absences'] > limit:
                            return "🔴 Failed (Attendance)"
                        
                        elif current_week < 15 and limit > 0 and 0 <= (limit - row['Absences']) <= 2:
                            return "🟠 Warning (Attendance)"
                    
                    
                    if current_week >= 15:
                        return "🟢 Passed" if row['Total Score'] >= 40 else "🟡 Failed (Grades)"
                    
                    
                    if pd.notnull(row['AI Final Prediction']):
                        proj_score = (row['G1']*(w1/100)) + (row['G2']*(w2/100)) + (row['AI Final Prediction']*(w3/100))
                        if proj_score < 40:
                            return "⚠️ High Risk (AI)"
                        elif proj_score < 55:
                            return "🟠 At Risk (AI)"
                            
                    return "🔵 Ongoing"

                df['Status'] = df.apply(get_status, axis=1)

                
                alerts = []
                
                if current_week < 15:
                    for index, row in df.iterrows():
                        
                        if limit > 0 and 0 <= (limit - row['Absences']) <= 2:
                            alerts.append({
                                "name": row['Name'], "type": "attendance", 
                                "msg": f"Attendance is at the borderline! {row['Absences']} absences (Limit: {int(limit)})", 
                                "details": {"absences": row['Absences'], "limit": int(limit)}
                            })
                        
                        
                        if pd.notnull(row['AI Final Prediction']):
                            proj_score = (row['G1']*(w1/100)) + (row['G2']*(w2/100)) + (row['AI Final Prediction']*(w3/100))
                            if proj_score < 40 and row['Status'] not in ["🔴 Failed (Attendance)", "🟡 Failed (Grades)"]:
                                alerts.append({
                                    "name": row['Name'], "type": "grade", 
                                    "msg": f"Critical AI Alert: Projected Total Score is {proj_score:.1f} (Fail Risk)", 
                                    "details": {"projected_score": round(proj_score, 1)}
                                })

                if alerts:
                    with st.expander(f"🔔 Action Required: {len(alerts)} Smart Notifications", expanded=True):
                        st.markdown("AI has identified students at risk. Generate intervention emails instantly.")
                        for alert in alerts:
                            col_a, col_b = st.columns([4, 1])
                            with col_a:
                                if alert['type'] == 'attendance': st.warning(f"**{alert['name']}** - {alert['msg']}")
                                else: st.error(f"**{alert['name']}** - {alert['msg']}")
                            with col_b:
                                if st.button("Generate Mail", key=f"btn_{alert['name']}_{alert['type']}"):
                                    with st.spinner("Writing..."):
                                        st.session_state['email_draft'] = generate_warning_email(groq_api_key, alert['name'], alert['type'], alert['details'])
                                        st.session_state['email_student'] = alert['name']
                                        
                        if 'email_draft' in st.session_state:
                            st.divider()
                            st.markdown(f"### ✉️ Draft Ready for **{st.session_state.get('email_student', '')}**")
                            st.text_area("You can edit before sending:", st.session_state['email_draft'], height=200)
                


                edited_df = st.data_editor(df, use_container_width=True, hide_index=True,
                                          disabled=["ID", "Name", "Total Score", "Status", "AI Final Prediction"])
                
                if st.button("💾 Save All Changes"):
                    st.session_state['students'][active_class] = edited_df.drop(columns=['Total Score', 'Status', 'AI Final Prediction']).to_dict('records')
                    save_data()
                    st.success("Changes saved successfully!")
                    st.rerun()

                
                csv_data = edited_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Class Data (CSV)",
                    data=csv_data,
                    file_name=f"{active_class}_Data_Week_{current_week}.csv",
                    mime="text/csv",
                    use_container_width=True 
                )
                

                st.divider()
                st.subheader("📈 Class Performance Insights")
                
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    st.write("**Attendance vs. Performance Correlation**")
                    fig1, ax1 = plt.subplots(figsize=(6, 4))
                    sns.regplot(x='Absences', y='Total Score', data=df, ax=ax1, scatter_kws={'alpha':0.6}, line_kws={'color':'red'})
                    ax1.set_title("Impact of Absences on Total Score")
                    st.pyplot(fig1)
                with col_c2:
                    st.write("**Class Score Spread**")
                    fig2, ax2 = plt.subplots(figsize=(6, 4))
                    sns.boxplot(y=df['Total Score'], color="#7eb0d5", ax=ax2)
                    ax2.set_title("Score Distribution Range")
                    st.pyplot(fig2)

                st.divider()
                col_c3, col_c4 = st.columns(2)
                with col_c3:
                    st.write("**Correlation Matrix**")
                    fig3, ax3 = plt.subplots(figsize=(6, 4))
                    corr_df = df[['G1', 'G2', 'Absences', 'Total Score']].corr()
                    sns.heatmap(corr_df, annot=True, cmap="coolwarm", fmt=".2f", vmin=-1, vmax=1, ax=ax3)
                    ax3.set_title("Variable Relationships")
                    st.pyplot(fig3)
                    
                with col_c4:
                    st.write("**AI Model Feature Importance**")
                    model = st.session_state.get('ml_model')
                    if model:
                        fig4, ax4 = plt.subplots(figsize=(6, 4))
                        importance = model.coef_
                        features_names = ['Grade Potantial', 'Absences']
                        sns.barplot(x=features_names, y=importance, palette="viridis", ax=ax4)
                        ax4.axhline(0, color='black', linestyle='-', linewidth=0.8)
                        ax4.set_title("What drives the AI's prediction?")
                        st.pyplot(fig4)
                    else:
                        st.info("AI Model not initialized.")
            else:
                st.info("No students enrolled. Use sidebar to add students.")
        else:
            st.warning("Please select or create a class to continue.")

    with tab2:
        if active_class and students:
            st.subheader("Student Detail & Comparison Report")
            std_list = df['Name'].tolist()
            sel_name = st.selectbox("Search Student Profile", std_list)
            row = df[df['Name'] == sel_name].iloc[0]
            
            class_avg = df['Total Score'].mean()
            diff = row['Total Score'] - class_avg
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Current Total Score", f"{row['Total Score']:.1f}", f"{diff:.1f} vs Class Mean", delta_color="normal")
            m2.metric("Absence Log", f"{row['Absences']} / {ci['total_sessions']}")
            m3.metric("Status", row['Status'])
            
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.write("**Student vs Class Mean**")
                compare_df = pd.DataFrame({
                    "Metric": ["G1", "G2", "Final", "Total Score"],
                    "Student": [row['G1'], row['G2'], row['G3'], row['Total Score']],
                    "Class": [df['G1'].mean(), df['G2'].mean(), df['G3'].mean(), class_avg]
                }).set_index("Metric")
                st.bar_chart(compare_df)
                
            with col_chart2:
                st.write("**Current vs. AI Predicted Final (G3)**")
                ai_pred_val = row['AI Final Prediction'] if pd.notnull(row['AI Final Prediction']) else 0
                trend_df = pd.DataFrame({
                    "Stage": ["Midterm 1 (Actual)", "Midterm 2 (Actual)", "Final (AI Predict)"],
                    "Score": [row['G1'], row['G2'], ai_pred_val]
                }).set_index("Stage")
                st.bar_chart(trend_df)
        else:
            st.info("Enroll students to view detailed analysis.")

    with tab3:
        st.subheader("ML Reference Data")
        try:
            ref_df = pd.read_csv("data/student_data.csv")
            for c in ['G1','G2','G3']: ref_df[c] = ref_df[c] * 5
            st.dataframe(ref_df[['sex','age','absences','G1','G2','G3']].head(50), use_container_width=True)
        except Exception as e:
            st.error(f"Reference data error: {e}")