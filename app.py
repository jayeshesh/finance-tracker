import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. SETUP & SECRETS ---
# Securely load the API Key
if "GEMINI_KEY" in st.secrets:
    MY_API_KEY = st.secrets["GEMINI_KEY"]
else:
    # Fallback for local testing (replace with your key if needed)
    MY_API_KEY = "AIzaSy..." 

genai.configure(api_key=MY_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="Business Daybook", page_icon="📈", layout="wide")
st.title("💰 AI Digital Daybook")

# Memory for processed entries
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None

# Date logic
today_str = datetime.now().strftime("%Y-%m-%d")
this_month = datetime.now().strftime("%Y-%m")

# --- 2. GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def save_data(new_df):
    # Fetch existing data from Google Sheets (ttl=0 clears cache)
    existing_data = conn.read(worksheet="Sheet1", ttl=0)
    
    # Add timestamps to new data
    new_df['Date'] = today_str
    new_df['Month'] = this_month
    new_df['Log_Time'] = datetime.now().strftime("%H:%M:%S")
    
    # Check if Item exists ON THE SAME DATE to aggregate (upsert)
    if not existing_data.empty:
        for index, row in new_df.iterrows():
            mask = (existing_data['Item'].str.lower() == row['Item'].lower()) & \
                   (existing_data['Date'] == row['Date'])
            
            if mask.any():
                existing_data.loc[mask, 'Amount'] += row['Amount']
            else:
                existing_data = pd.concat([existing_data, pd.DataFrame([row])], ignore_index=True)
        updated_df = existing_data
    else:
        updated_df = new_df
    
    # Write back to Sheets
    conn.update(worksheet="Sheet1", data=updated_df)
    st.success("✅ Synced to Google Sheets!")
    st.session_state.processed_data = None

# --- 3. NAVIGATION TABS ---
tab1, tab2 = st.tabs(["📝 Daily Entry", "📊 Monthly Reports"])

with tab1:
    st.subheader(f"Log for Today: {today_str}")
    user_text = st.text_area("Enter expenses (e.g., 5000 to Ravi for plumbing)", height=100)

    if st.button("Analyze Spending", key="analyze_btn"):
        if user_text:
            prompt = f"""
                Extract expenses from: "{user_text}"
                Return ONLY a JSON list with: "Item", "Category", "Amount". 
                Example: [{{ "Item": "Ravi Plumbing", "Category": "Others", "Amount": 5000 }}]
            """
            with st.spinner("AI is thinking..."):
                response = model.generate_content(prompt)
                try:
                    raw_data = response.text.strip().replace('```json', '').replace('```', '')
                    st.session_state.processed_data = json.loads(raw_data)
                except: st.error("AI could not read the text. Try again.")

    if st.session_state.processed_data:
        df = pd.DataFrame(st.session_state.processed_data)
        st.table(df)
        if st.button("Confirm & Save to History", key="save_history_btn"):
            save_data(df)
            st.rerun()

    st.divider()
    st.subheader("Today's Summary")
    # Fetch live data from Sheets for today only
    live_df = conn.read(worksheet="Sheet1", ttl=5)
    if not live_df.empty and 'Date' in live_df.columns:
        today_data = live_df[live_df['Date'] == today_str]
        st.dataframe(today_data, use_container_width=True)
    else:
        st.info("No records for today yet.")

with tab2:
    st.subheader("📈 Monthly Performance")
    # Fetch all data from Sheets
    report_df = conn.read(worksheet="Sheet1", ttl=5)
    
    if not report_df.empty and 'Month' in report_df.columns:
        # Filter for current month
        month_df = report_df[report_df['Month'] == this_month]
        
        monthly_total = month_df['Amount'].sum()
        st.metric(f"Total Spent in {this_month}", f"₹{monthly_total}")

        col1, col2 = st.columns(2)
        with col1:
            st.write("### Spending by Category")
            cat_data = month_df.groupby('Category')['Amount'].sum()
            st.bar_chart(cat_data)
        
        with col2:
            st.write("### Daily Trend")
            daily_trend = month_df.groupby('Date')['Amount'].sum()
            st.line_chart(daily_trend)
            
        # Add a download button for Tally/Excel
        st.download_button("Download Full History (Excel)", report_df.to_csv(index=False), "finance_history.csv")
    else:
        st.info("No data available for reports yet.")
