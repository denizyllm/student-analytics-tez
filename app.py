import streamlit as st
import psycopg2
import datetime

DB_URL = st.secrets["DB_URL"]

st.set_page_config(page_title="Stray Animal System", page_icon="🐾", layout="wide")

@st.cache_resource
def init_connection():
    return psycopg2.connect(DB_URL)

try:
    conn = init_connection()
    cursor = conn.cursor()
    
    st.title("🐾 Stray Animal Health & Foster Dashboard")
    st.markdown("---")
    
    if 'success_msg' in st.session_state:
        st.success(st.session_state['success_msg'])
        del st.session_state['success_msg']
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 System Overview", 
        "🚨 Alerts & Reports", 
        "➕ Register Volunteer", 
        "🐶 Register Animal",
        "💉 Add Vaccine Record",
        "🤝 Assign Foster"
    ])
    
    with tab1:
        st.subheader("👥 All Foster Volunteers")
        cursor.execute("SELECT volunteer_id AS \"ID\", name AS \"Name\", phone AS \"Phone\", address AS \"Address\", capacity AS \"Capacity\" FROM Foster_Volunteers ORDER BY volunteer_id;")
        volunteers = cursor.fetchall()
        if volunteers:
            st.dataframe([dict(zip([desc[0] for desc in cursor.description], row)) for row in volunteers], use_container_width=True)
        else:
            st.info("There are no registered volunteers in the system yet.")

        st.divider()

        st.subheader("🐾 All Registered Animals")
        cursor.execute("""
            SELECT a.animal_id AS "ID", a.name AS "Name", a.age AS "Age", a.gender AS "Gender", 
                   t.type_name AS "Species", a.health_status AS "Health Status", a.status AS "Foster Status",
                   COALESCE(f.name, 'Unassigned') AS "Foster Volunteer"
            FROM Animals a
            LEFT JOIN Animal_Types t ON a.type_id = t.type_id
            LEFT JOIN Foster_Volunteers f ON a.volunteer_id = f.volunteer_id
            ORDER BY a.animal_id;
        """)
        animals = cursor.fetchall()
        if animals:
            st.dataframe([dict(zip([desc[0] for desc in cursor.description], row)) for row in animals], use_container_width=True)
        else:
            st.info("There are no animals registered in the system yet.")
    
    with tab2:
        st.subheader("Capacity Warning System")
        if st.button("Show Volunteers at Max Capacity"):
            query1 = """
            SELECT f.name AS "Volunteer Name", f.capacity AS "Max Capacity", COUNT(a.animal_id) AS "Current Fosters"
            FROM Foster_Volunteers f
            LEFT JOIN Animals a ON f.volunteer_id = a.volunteer_id
            GROUP BY f.name, f.capacity
            HAVING COUNT(a.animal_id) >= f.capacity;
            """
            cursor.execute(query1)
            results1 = cursor.fetchall()
            if results1:
                st.dataframe([dict(zip([desc[0] for desc in cursor.description], row)) for row in results1], use_container_width=True)
            else:
                st.success("All volunteers' capacity is currently at a safe level!")

        st.divider()

        st.subheader("Upcoming Vaccinations (Next 30 Days)")
        if st.button("Get Urgent Vaccination List"):
            query2 = """
            WITH Upcoming_Vaccines AS (
                SELECT animal_id, vaccine_name, next_due_date
                FROM Vaccination_Records
                WHERE next_due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days'
            )
            SELECT a.name AS "Animal Name", f.name AS "Volunteer Name", u.vaccine_name AS "Vaccine", u.next_due_date AS "Due Date"
            FROM Animals a
            INNER JOIN Upcoming_Vaccines u ON a.animal_id = u.animal_id
            LEFT JOIN Foster_Volunteers f ON a.volunteer_id = f.volunteer_id
            ORDER BY u.next_due_date ASC;
            """
            cursor.execute(query2)
            results2 = cursor.fetchall()
            if results2:
                st.dataframe([dict(zip([desc[0] for desc in cursor.description], row)) for row in results2], use_container_width=True)
            else:
                st.success("There is no urgent vaccine that needs to be administered within the next 30 days!")
    
    with tab3:
        st.subheader("Add New Foster Volunteer")
        with st.form("new_volunteer_form"):
            v_name = st.text_input("Full Name")
            v_phone = st.text_input("Phone Number")
            v_address = st.text_input("Address")
            v_capacity = st.number_input("Max Capacity", min_value=1, step=1)
            submit_volunteer = st.form_submit_button("Save to Database")
            
            if submit_volunteer:
                cursor.execute("INSERT INTO Foster_Volunteers (name, phone, address, capacity) VALUES (%s, %s, %s, %s)", (v_name, v_phone, v_address, v_capacity))
                conn.commit()
                st.session_state['success_msg'] = f"{v_name} successfully added to the live database!"
                st.rerun()
    
    with tab4:
        st.subheader("Register a New Rescued Animal")
        with st.form("new_animal_form"):
            a_name = st.text_input("Animal Name")
            a_age = st.number_input("Age", min_value=0, step=1)
            a_gender = st.selectbox("Gender", ["Male", "Female"])
            a_type = st.selectbox("Species", options=[1, 2, 3], format_func=lambda x: "Dog" if x==1 else ("Cat" if x==2 else "Bird"))
            a_health = st.selectbox("Health Status", ["Healthy", "Under Treatment", "Critical"])
            submit_animal = st.form_submit_button("Save to Database")
            
            if submit_animal:
                cursor.execute("INSERT INTO Animals (name, age, gender, type_id, health_status, arrival_date, status) VALUES (%s, %s, %s, %s, %s, CURRENT_DATE, 'Available')", (a_name, a_age, a_gender, a_type, a_health))
                conn.commit()
                st.session_state['success_msg'] = f"{a_name} successfully registered!"
                st.rerun()

    with tab5:
        st.subheader("Add New Vaccination Record")
        cursor.execute("SELECT animal_id, name FROM Animals ORDER BY name;")
        all_animals = cursor.fetchall()
        
        if all_animals:
            animal_dict = {f"{a[1]} (ID: {a[0]})": a[0] for a in all_animals}
            
            with st.form("vaccine_form"):
                selected_animal = st.selectbox("Select Animal", list(animal_dict.keys()))
                vac_name = st.text_input("Vaccine Name (e.g. Rabies, Feline Viral)")
                vac_date = st.date_input("Vaccination Date", datetime.date.today())
                next_due = st.date_input("Next Due Date", datetime.date.today().replace(year=datetime.date.today().year + 1))
                
                submit_vaccine = st.form_submit_button("Save Vaccine Record")
                
                if submit_vaccine:
                    animal_id = animal_dict[selected_animal]
                    cursor.execute("INSERT INTO Vaccination_Records (animal_id, vaccine_name, vaccination_date, next_due_date) VALUES (%s, %s, %s, %s)", (animal_id, vac_name, vac_date, next_due))
                    conn.commit()
                    st.session_state['success_msg'] = f"Vaccination record for {selected_animal.split(' (')[0]} successfully added!"
                    st.rerun()
        else:
            st.warning("You need to register an animal first before adding a vaccine record.")

    with tab6:
        st.subheader("Assign Animal to a Foster Volunteer")
        
        cursor.execute("SELECT animal_id, name FROM Animals WHERE volunteer_id IS NULL ORDER BY name;")
        unassigned_animals = cursor.fetchall()
        
        cursor.execute("""
            SELECT f.volunteer_id, f.name 
            FROM Foster_Volunteers f
            LEFT JOIN Animals a ON f.volunteer_id = a.volunteer_id
            GROUP BY f.volunteer_id, f.name, f.capacity
            HAVING COUNT(a.animal_id) < f.capacity
            ORDER BY f.name;
        """)
        available_volunteers = cursor.fetchall()
        
        if unassigned_animals and available_volunteers:
            unassigned_dict = {f"{a[1]} (ID: {a[0]})": a[0] for a in unassigned_animals}
            volunteer_dict = {f"{v[1]} (ID: {v[0]})": v[0] for v in available_volunteers}
            
            with st.form("assign_foster_form"):
                selected_unassigned = st.selectbox("Select Unassigned Animal", list(unassigned_dict.keys()))
                selected_volunteer = st.selectbox("Select Foster Volunteer", list(volunteer_dict.keys()))
                
                submit_assign = st.form_submit_button("Confirm Assignment")
                
                if submit_assign:
                    anim_id = unassigned_dict[selected_unassigned]
                    vol_id = volunteer_dict[selected_volunteer]
                    
                    cursor.execute("UPDATE Animals SET volunteer_id = %s, status = 'Fostered' WHERE animal_id = %s", (vol_id, anim_id))
                    conn.commit()
                    st.session_state['success_msg'] = f"Successfully assigned {selected_unassigned.split(' (')[0]} to {selected_volunteer.split(' (')[0]}!"
                    st.rerun()
        else:
            if not unassigned_animals:
                st.info("There are currently no unassigned animals. Everyone has a foster home!")
            if not available_volunteers:
                st.error("All volunteers are currently at maximum capacity! You cannot assign any more animals.")
        
        st.divider()
        
        st.subheader("Unassign Animal from Foster")
        
        cursor.execute("SELECT animal_id, name FROM Animals WHERE volunteer_id IS NOT NULL ORDER BY name;")
        assigned_animals = cursor.fetchall()
        
        if assigned_animals:
            assigned_dict = {f"{a[1]} (ID: {a[0]})": a[0] for a in assigned_animals}
            
            with st.form("unassign_foster_form"):
                selected_assigned = st.selectbox("Select Animal to Unassign", list(assigned_dict.keys()))
                
                submit_unassign = st.form_submit_button("Unassign")
                
                if submit_unassign:
                    anim_id = assigned_dict[selected_assigned]
                    cursor.execute("UPDATE Animals SET volunteer_id = NULL, status = 'Available' WHERE animal_id = %s", (anim_id,))
                    conn.commit()
                    st.session_state['success_msg'] = f"Successfully unassigned {selected_assigned.split(' (')[0]}!"
                    st.rerun()
        else:
            st.info("There are currently no assigned animals.")

except Exception as e:
    if conn:
        conn.rollback()
    st.error(f"Connection Error: {e}")