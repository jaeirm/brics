import streamlit as st
from data_handler import load_data, save_data
from calculations import calculate_currency_values, recalculate_scenario
from ui_components import create_sidebar, display_header, display_data_overview, display_scenario_analysis
from visualization import visualize_data
from methodology import show_methodology
from forex_rates import display_forex_tables
from BC_ui import display_transfer_tab
import pandas as pd
import initialize

# Initialize app state
initialize.setup_session_state()

# Ensure balances are initialized
if "balances" not in st.session_state:
    st.session_state.balances = {currency: 1000 for currency in ["INR", "CNY", "ZAR", "BRL", "RUB"]}  # Initial Balance

# Create the sidebar
calculation_mode, use_csv = create_sidebar()

# Display app header
display_header(calculation_mode)

# Load data
df = load_data(use_csv)


if not df.empty:
    # Run calculations on the data
    df = calculate_currency_values(df, calculation_mode)

    # Ensure Exchange Rate column exists before using it
    if "Exchange_Rate_BC" in df.columns:
        st.session_state.ex_rates = df.set_index("Country")["Exchange_Rate_BC"].to_dict()
        # st.write("Stored Exchange Rates:", st.session_state.ex_rates)
    else:
        st.warning("Exchange rate column missing in dataset. Please check calculations.")

    # Save the updated dataset
    save_data(df)

    # Create tabs for different views
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["Data Overview", "Scenario Analysis", "Visualization", "Methodology", "Exchange Rates", "Transfer"]
    )

    with tab1:
        display_data_overview(df, calculation_mode)

    with tab2:
        display_scenario_analysis(df, calculation_mode)

    with tab3:
        visualize_data(df, calculation_mode)

    with tab4:
        show_methodology()

    with tab5:
        display_forex_tables(df)

    with tab6:
        # Use the new display_transfer_tab function
        display_transfer_tab()

# Hide Streamlit branding
st.markdown("""
    <style>
        /* Hide the top-right menu button */
        header [data-testid="stToolbar"] {visibility: hidden;}

        /* Hide the deploy/share button */
        footer {visibility: hidden;}
        header
            {
                display: none !important;
                height: 0px !important;
            }
            div[data-testid="stVerticalBlock"] div:has(div.fixed-header)
            {
            top: 0;}
    </style>
""", unsafe_allow_html=True)
