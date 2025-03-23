import streamlit as st
import pandas as pd

def setup_session_state():
    """Initialize session state variables if they don't exist"""
    
    # Initialize session state if not already set
    if "df" not in st.session_state:
        st.session_state.df = pd.DataFrame()
        st.session_state.total_gdp = 0
        st.session_state.brics_currency_price = 0
    
    # Adding weights to session state for ALL indicators
    if "weights" not in st.session_state:
        st.session_state.weights = {
            "GDP_weight": 1.0,            # Base weight for GDP contribution
            "BOT_weight": 1.0,            # Balance of Trade weight
            "Exports_weight": 1.0,        # Direct weight for exports
            "Imports_weight": 1.0,        # Direct weight for imports
            "Inflation_weight": 1.0,      # Inflation weight
            "Interest_Rate_weight": 1.0,  # Interest Rate weight
            "Forex_Reserves_weight": 1.0,  # Foreign Exchange Reserves weight
            "Debt_to_GDP_weight": 1.0,    # Debt to GDP ratio weight
            "Stability_weight": 1.0       # Economic stability weight
        }
    
    # Store baseline value for comparison
    if "baseline_currency_value" not in st.session_state:
        st.session_state.baseline_currency_value = 0
