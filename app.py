import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import os
from datetime import datetime

# --- SETUP ---
MY_API_KEY = "AIzaSyDnMGvmbrlUTb-viegZ87I0WfjhezX8G2s"
genai.configure(api_key=MY_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

st.set_page_config(page_title="Business Daybook", page_icon="📈", layout="wide")
st.title("📂 Digital Daybook & Finance Tracker")

# Initialize Memory
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None

# --- NEW DATE LOGIC ---
today_str = datetime.now().strftime("%Y-%m-%d")
this_month = datetime.now().strftime("%Y-%m")

# --- UPDATED SAVE FUNCTION ---
def save_data(new_df):
    file_path = "my_expenses.csv"
    # Add Date, Month, and exact Time for every entry
    new_df['Date'] = today_str
    new_df['Month'] = this_month
    new_df['Log_Time'] = datetime.now().strftime("%H:%M:%S")
    
    if os.path.exists(file_path):
        existing_df = pd.read_csv(file_path)
        # Check if item exists ON THE SAME DATE before updating
        for index, row in new_df.iterrows():
            mask = (existing_df['Item'].str.lower() == row['Item'].lower()) & (existing_df['Date'] == row['Date'])
            if mask.any():
                existing_df.loc[mask, 'Amount'] += row['Amount']
            else:
                existing_df = pd.concat([existing_df, pd.DataFrame([row])], ignore_index=True)
        existing_df.to_csv(file_path, index=False)
    else:
        new_df.to_csv(file_path, index=False)
    
    st.success(f"✅ Records for {today_str} Updated!")
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

