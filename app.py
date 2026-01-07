import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import os
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- SETUP ---
if "GEMINI_KEY" in st.secrets:
    MY_API_KEY = st.secrets["GEMINI_KEY"]
else:
    # This fall-back allows you to still run it locally for testing
    MY_API_KEY = "AIzaSyDnMGvmbrlUTb-viegZ87I0WfjhezX8G2s"

genai.configure(api_key=MY_API_KEY)

model = genai.GenerativeModel('gemini-1.5-flash')
st.set_page_config(page_title="Business Daybook", page_icon="📈", layout="wide")
st.title("📂 Digital Daybook & Finance Tracker")

# Initialize Memory
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None

# --- NEW DATE LOGIC ---
today_str = datetime.now().strftime("%Y-%m-%d")
this_month = datetime.now().strftime("%Y-%m")

# --- UPDATED SAVE FUNCTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def save_data(new_df):
    # Fetch existing data from the sheet
    existing_data = conn.read(worksheet="Sheet1")
    
    # Add new info
    new_df['Date'] = today_str
    new_df['Month'] = this_month
    new_df['Log_Time'] = datetime.now().strftime("%H:%M:%S")
    
    # Combine old and new
    updated_df = pd.concat([existing_data, new_df], ignore_index=True)
    
    # 2. Write back to Google Sheets
    conn.update(worksheet="Sheet1", data=updated_df)
    
    st.success("✅ Data synced to Google Sheets!")
    st.session_state.processed_data = None

# --- NAVIGATION TABS ---
tab1, tab2 = st.tabs(["📝 Daily Entry", "📊 Monthly Reports"])

with tab1:
    st.subheader(f"Log for Today: {today_str}")
    user_text = st.text_area("What payments were made? (e.g., 5000 to Ravi for plumbing)", height=100)

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
                except: st.error("AI error. Try again.")

    if st.session_state.processed_data:
        df = pd.DataFrame(st.session_state.processed_data)
        st.table(df)
        if st.button("Confirm & Save to History", key="save_history_btn"):
            save_data(df)
            st.rerun()

    st.divider()
    st.subheader("Today's Summary")
    if os.path.exists("my_expenses.csv"):
        history_df = pd.read_csv("my_expenses.csv")
        # ONLY SHOW TODAY'S DATA HERE
        today_data = history_df[history_df['Date'] == today_str]
        st.dataframe(today_data, use_container_width=True)
    else:
        st.info("No records for today yet.")

with tab2:
    st.subheader("📈 Monthly Performance")
    if os.path.exists("my_expenses.csv"):
        full_df = pd.read_csv("my_expenses.csv")
        
        # Monthly Totals
        monthly_total = full_df[full_df['Month'] == this_month]['Amount'].sum()
        st.metric(f"Total Spending in {this_month}", f"₹{monthly_total}")

        # Basic Charts
        st.write("### Spending by Category")
        cat_data = full_df[full_df['Month'] == this_month].groupby('Category')['Amount'].sum()
        st.bar_chart(cat_data)
        
        st.write("### Daily Trend (This Month)")
        daily_trend = full_df[full_df['Month'] == this_month].groupby('Date')['Amount'].sum()
        st.line_chart(daily_trend)
    else:
        st.info("No data available for reports.")

