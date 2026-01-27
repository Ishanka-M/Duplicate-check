import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import io
import time
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="EFL Picking Verification", page_icon="📦", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stDataFrame { border: 1px solid #393e46; border-radius: 10px; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #222831; color: #888888; text-align: center; padding: 10px; font-size: 12px; z-index: 100; }
    .metric-card { background-color: #1e2129; padding: 15px; border-radius: 10px; text-align: center; }
    .stButton button { width: 100%; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- GOOGLE SHEETS CONNECTION ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_gspread_client():
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

try:
    client = get_gspread_client()
    spreadsheet = client.open("streamlit_DB")
    sheet = spreadsheet.worksheet("Sheet1")
except Exception as e:
    st.error(f"Error connecting to Google Sheets: {e}")
    st.stop()

def to_excel(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    writer.close()
    return output.getvalue()

# --- SIDEBAR NAVIGATION ---
st.sidebar.image("efl_logo.png", use_container_width=True)
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigation", ["📤 Upload Data", "🔍 Search & History", "🗑️ Manage Records", "⚙️ Admin Panel"])

# --- MAIN HEADER ---
col_logo, col_title = st.columns([0.15, 0.85])
with col_logo:
    st.image("efl_logo.png", width=100)
with col_title:
    st.title("Picking Verification System")
    st.write("EFL Logistics | Verification Portal")
st.markdown("---")

# --- PAGE 1: UPLOAD DATA ---
if page == "📤 Upload Data":
    uploaded_file = st.file_uploader("Daily Excel File එක මෙතනට දාන්න", type=["xlsx", "xls"])
    
    if uploaded_file:
        with st.spinner('Processing file...'):
            new_df = pd.read_excel(uploaded_file)
            new_df.columns = new_df.columns.str.strip() 
            
            existing_data = sheet.get_all_records()
            existing_df = pd.DataFrame(existing_data)
            if not existing_df.empty:
                existing_df.columns = existing_df.columns.str.strip()

        if 'Pallet' in new_df.columns:
            duplicate_pallets = []
            if not existing_df.empty and 'Pallet' in existing_df.columns:
                duplicate_pallets = new_df[new_df['Pallet'].isin(existing_df['Pallet'])]['Pallet'].tolist()

            if duplicate_pallets:
                # මෙහිදී column order එක වෙනස් නොකර සාමාන්‍ය පරිදි පෙන්වයි
                existing_duplicates = existing_df[existing_df['Pallet'].isin(duplicate_pallets)]

                st.error(f"⚠️ පද්ධතියේ දැනටමත් පවතින (Duplicate) Pallets {len(existing_duplicates)} ක් හමු වුණා!")
                st.markdown("### 📋 පද්ධතියේ දැනට පවතින විස්තර (Existing Records)")
                st.dataframe(existing_duplicates, use_container_width=True)
                
                col_up1, col_up2 = st.columns(2)
                with col_up1:
                    if st.button("✅ Yes, Save Everything (Ignore Duplicates)", type="primary"):
                        sheet.append_rows(new_df.astype(str).values.tolist())
                        st.balloons(); st.success("දත්ත ඇතුළත් කළා!")
                with col_up2:
                    st.download_button("📥 Download Duplicate Details", data=to_excel(existing_duplicates), file_name="duplicates.xlsx")
            else:
                st.success("✅ No duplicates found.")
                if st.button("Save Data Now", type="primary"):
                    sheet.append_rows(new_df.astype(str).values.tolist())
                    st.balloons(); st.success("දත්ත ඇතුළත් කළා!")
        else:
            st.error("වැරදි Format එකක්! 'Pallet' column එක පරීක්ෂා කරන්න.")

# --- PAGE 2: SEARCH & HISTORY ---
elif page == "🔍 Search & History":
    st.subheader("🔍 Search & Day Summary")
    with st.spinner('Loading data...'):
        all_data = pd.DataFrame(sheet.get_all_records())

    if not all_data.empty:
        all_data.columns = all_data.columns.str.strip()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Pallets", len(all_data))
        c2.metric("Total Actual Qty", int(all_data['Actual Qty'].sum()) if 'Actual Qty' in all_data.columns else 0)
        c3.metric("Unique Load IDs", all_data['Load Id'].nunique() if 'Load Id' in all_data.columns else 0)

        st.markdown("---")
        search_query = st.text_input("Pallet ID, Load ID හෝ ඕනෑම විස්තරයක් ඇතුළත් කර සොයන්න...")

        if search_query:
            filtered_df = all_data[all_data.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]
            st.write(f"ප්‍රතිඵල: {len(filtered_df)}")
            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.dataframe(all_data, use_container_width=True)

        download_df = filtered_df if search_query else all_data
        st.download_button("📥 Download View as Excel", data=to_excel(download_df), file_name="report.xlsx")
    else:
        st.info("පද්ධතියේ තවමත් දත්ත නැත.")

# --- PAGE 3: MANAGE RECORDS ---
elif page == "🗑️ Manage Records":
    st.subheader("🗑️ Delete Records")
    all_data = pd.DataFrame(sheet.get_all_records())
    
    if not all_data.empty:
        all_data.columns = all_data.columns.str.strip()
        target_pallet = st.selectbox("මකා දැමිය යුතු Pallet ID එක තෝරන්න", ["-- Select --"] + all_data['Pallet'].astype(str).tolist())
        
        if target_pallet != "-- Select --":
            row_to_delete = all_data[all_data['Pallet'].astype(str) == target_pallet]
            # Table එක මුල් ආකාරයෙන්ම පෙන්වයි
            st.table(row_to_delete)
            
            if st.button("🚨 Delete Permanently", type="secondary"):
                with st.spinner('Deleting...'):
                    cell = sheet.find(str(target_pallet))
                    sheet.delete_rows(cell.row)
                    st.success(f"Pallet {target_pallet} ඉවත් කළා!")
                    time.sleep(1)
                    st.rerun()
    else:
        st.info("මකා දැමීමට දත්ත නැත.")

# --- PAGE 4: ADMIN PANEL ---
elif page == "⚙️ Admin Panel":
    st.subheader("⚙️ System Maintenance & Backup")
    if 'admin_authenticated' not in st.session_state:
        st.session_state['admin_authenticated'] = False

    if not st.session_state['admin_authenticated']:
        password_input = st.text_input("Admin Password:", type="password")
        if st.button("Login"):
            if password_input == "efl123":
                st.session_state['admin_authenticated'] = True
                st.rerun()
            else:
                st.error("වැරදි මුරපදයක්!")
    else:
        if st.sidebar.button("Logout Admin"):
            st.session_state['admin_authenticated'] = False
            st.rerun()

        all_vals = sheet.get_all_values()
        if len(all_vals) > 1:
            st.warning("⚠️ Backup කර Clear කිරීමට මම එකඟ වෙමි.")
            confirm_check = st.checkbox("Confirm Action")
            if st.button("🚀 Run Manual Backup & Clear Now", type="primary"):
                if confirm_check:
                    now_str = datetime.now().strftime('%Y-%m-%d_%H-%M')
                    backup_name = f"Manual_Backup_{now_str}"
                    new_ws = spreadsheet.add_worksheet(title=backup_name, rows=len(all_vals)+10, cols=len(all_vals[0])+5)
                    new_ws.update(all_vals)
                    header = all_vals[0]
                    sheet.clear()
                    sheet.append_row(header)
                    st.balloons(); st.success("පද්ධතිය Reset කරන ලදී."); time.sleep(2); st.rerun()
        else:
            st.info("දත්ත නැත.")

st.markdown(f'<div class="footer">Developed by Ishanka Madusanka | 2026</div>', unsafe_allow_html=True)
