import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
from datetime import datetime

# --- Configuration ---
st.set_page_config(
    page_title="Receipt Analyzer",
    page_icon="🧾",
    layout="wide"
)

API_BASE_URL = "http://127.0.0.1:8000"

# --- Helper Functions ---
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def get_all_receipts(sort_by="transaction_date", sort_order="desc"):
    """Fetches all receipts from the backend."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/receipts",
            params={"sort_by": sort_by, "sort_order": sort_order, "limit": 100}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to API: {e}")
        return []

def get_summary_data():
    """Fetches aggregation summary from the backend."""
    try:
        response = requests.get(f"{API_BASE_URL}/receipts/summary")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to API: {e}")
        return None

# --- Main Application UI ---
local_css("style.css")

st.title("🧾 Receipt Analyzer")
st.markdown("Upload, analyze, and visualize your spending from receipts and bills.")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📤 Upload New Receipt", "🔍 Browse & Search"])

# --- Tab 1: Dashboard & Analytics ---
with tab1:
    st.header("Spending Analysis Dashboard")
    summary_data = get_summary_data()

    if summary_data and summary_data['receipt_count'] > 0:
        # --- Filters ---
        # In a real scenario, you'd connect these to filter the data.
        # For now, they are placeholders.
        c1, c2 = st.columns(2)
        with c1:
            st.date_input("Event Date", (datetime(2023, 9, 28), datetime(2023, 10, 18)))
        with c2:
            st.selectbox("Events", ["All"])

        st.divider()

        # --- Main Layout ---
        col_left, col_right = st.columns([1, 1.2])

        with col_left:
            # --- Metrics ---
            st.markdown('<div class="card metric-card"><h3>Total Spend</h3><p>₹{:.2f}</p></div>'.format(summary_data['total_spend']), unsafe_allow_html=True)
            st.markdown('<div class="card metric-card"><h3>Total Receipts</h3><p>{}</p></div>'.format(summary_data['receipt_count']), unsafe_allow_html=True)
            
            # --- Vendor Frequency Chart ---
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Vendor Frequency")
            vendor_freq = requests.get(f"{API_BASE_URL}/receipts/vendor-frequencies").json()
            if vendor_freq:
                freq_df = pd.DataFrame(list(vendor_freq.items()), columns=['Vendor', 'Count'])
                fig = px.bar(freq_df, x='Vendor', y='Count', title="Number of Visits per Vendor")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No vendor frequency data available.")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_right:
            # --- Spend by Vendor Pie Chart ---
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Spend by Vendor")
            spend_by_vendor = summary_data.get("spend_by_vendor", {})
            if spend_by_vendor:
                vendor_spend_df = pd.DataFrame(list(spend_by_vendor.items()), columns=['Vendor', 'Total Spend'])
                fig = px.pie(vendor_spend_df, values='Total Spend', names='Vendor', title='Overall Vendor Spending Distribution')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No vendor data to display.")
            st.markdown('</div>', unsafe_allow_html=True)

            # --- Top 5 Vendors by Spend ---
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Top 5 Vendors by Spend")
            if spend_by_vendor:
                top_5_vendors = vendor_spend_df.nlargest(5, 'Total Spend')
                
                fig, ax = plt.subplots()
                ax.barh(top_5_vendors['Vendor'], top_5_vendors['Total Spend'], color='skyblue')
                ax.invert_yaxis() # To display the highest at the top
                ax.set_xlabel('Total Spend (₹)')
                ax.set_title('Top 5 Vendors by Spend')
                st.pyplot(fig, use_container_width=True)
            else:
                st.info("No spending data by vendor available.")
            st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.info("No receipts found. Upload a receipt to see your dashboard.")

    # Export buttons
    st.write("Export Data:")
    col1, col2 = st.columns(2)
    col1.download_button(
        "Download as CSV",
        data=requests.get(f"{API_BASE_URL}/receipts/export-csv").content,
        file_name="receipts_export.csv",
        mime="text/csv"
    )
    col2.download_button(
        "Download as JSON",
        data=requests.get(f"{API_BASE_URL}/receipts/export-json").content,
        file_name="receipts_export.json",
        mime="application/json"
    )


# --- Tab 2: Upload New Receipt ---
with tab2:
    st.header("Upload a Receipt or Bill")
    uploaded_file = st.file_uploader(
        "Select a file (.jpg, .png, .pdf, .txt)",
        type=["jpg", "jpeg", "png", "pdf", "txt"]
    )

    if uploaded_file:
        st.write("---")
        st.image(uploaded_file, caption="Preview (first page for PDF)", use_column_width=False, width=300)

        if st.button("Process and Save Receipt"):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            
            with st.spinner("🚀 Analyzing file... This may take a moment."):
                try:
                    response = requests.post(f"{API_BASE_URL}/receipts/upload", files=files)
                    
                    if response.status_code == 201:
                        data = response.json()
                        st.success("✅ Receipt processed successfully!")
                        st.json(data)
                        st.info("Data saved to database. Check the Dashboard and Browse tabs.")
                    else:
                        error_detail = response.json().get("detail", "Unknown error")
                        st.error(f"⚠️ Processing Failed (Status {response.status_code}): {error_detail}")

                except requests.exceptions.RequestException as e:
                    st.error(f"Failed to connect to the backend: {e}")

# --- Tab 3: Browse & Search All Receipts ---
with tab3:
    st.header("All Processed Receipts")

    # Sorting options
    col_sort1, col_sort2 = st.columns(2)
    with col_sort1:
        sort_by = st.selectbox("Sort by", ["transaction_date", "total_amount", "vendor", "id"], index=0)
    with col_sort2:
        sort_order = st.selectbox("Order", ["desc", "asc"], index=0)

    # Fetch and display data
    all_receipts = get_all_receipts(sort_by, sort_order)
    
    if all_receipts:
        # Create a header
        header_cols = st.columns([1, 3, 2, 2, 1])
        header_cols[0].write("**ID**")
        header_cols[1].write("**Vendor**")
        header_cols[2].write("**Date**")
        header_cols[3].write("**Amount**")
        header_cols[4].write("**Actions**")

        st.markdown("---")

        for receipt in all_receipts:
            col1, col2, col3, col4, col5 = st.columns([1, 3, 2, 2, 1])
            with col1:
                st.write(receipt['id'])
            with col2:
                st.write(receipt['vendor'])
            with col3:
                st.write(receipt['transaction_date'])
            with col4:
                st.write(f"₹{receipt['total_amount']:.2f}")
            with col5:
                if st.button("Delete", key=f"delete_{receipt['id']}"):
                    try:
                        response = requests.delete(f"{API_BASE_URL}/receipts/{receipt['id']}")
                        if response.status_code == 200:
                            st.success(f"Receipt ID {receipt['id']} deleted.")
                            st.rerun()
                        else:
                            st.error(f"Error deleting receipt: {response.text}")
                    except requests.exceptions.RequestException as e:
                        st.error(f"API connection error: {e}")
    else:
        st.info("No receipts found in the database.")
