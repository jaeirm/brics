import streamlit as st
import pandas as pd

def create_sidebar():
    """Create and handle the sidebar UI components"""
    st.sidebar.title("BRICS Framework Settings")
    
    # Data source selection
    use_csv = st.sidebar.radio("Select Data Source:", ["Use API", "Upload CSV"])
    
    # Calculation mode selection
    calculation_mode = st.sidebar.radio(
        "Select Calculation Mode:", 
        ["Basic Indicators", "Advanced Indicators", "Expert Indicators"]
    )
    
    # Add weight customization in sidebar with collapsible sections
    st.sidebar.title("Indicator Weights")
    st.sidebar.info("Adjust the importance of each indicator in the currency calculation")

    # Base weights (available in all modes)
    with st.sidebar.expander("Base Weights", expanded=True):
        st.session_state.weights["GDP_weight"] = st.slider(
            "GDP Weight", 0.0, 2.0, st.session_state.weights["GDP_weight"], 0.1, 
            help="Adjusts the importance of GDP in determining a country's base weight"
        )
        st.session_state.weights["BOT_weight"] = st.slider(
            "Balance of Trade Weight", 0.0, 2.0, st.session_state.weights["BOT_weight"], 0.1,
            help="Adjusts the importance of trade balance in the formula"
        )
        st.session_state.weights["Exports_weight"] = st.slider(
            "Exports Weight", 0.0, 2.0, st.session_state.weights["Exports_weight"], 0.1,
            help="Adjusts the importance of exports when calculating trade balance"
        )
        st.session_state.weights["Imports_weight"] = st.slider(
            "Imports Weight", 0.0, 2.0, st.session_state.weights["Imports_weight"], 0.1,
            help="Adjusts the importance of imports when calculating trade balance"
        )

    # Advanced weights (only visible in advanced and expert modes)
    if calculation_mode in ["Advanced Indicators", "Expert Indicators"]:
        with st.sidebar.expander("Advanced Weights", expanded=True):
            st.session_state.weights["Inflation_weight"] = st.slider(
                "Inflation CPI Weight", 0.0, 2.0, st.session_state.weights["Inflation_weight"], 0.1,
                help="Adjusts the importance of Inflation CPI in the formula"
            )
            st.session_state.weights["Interest_Rate_weight"] = st.slider(
                "Real Interest Rate Weight", 0.0, 2.0, st.session_state.weights["Interest_Rate_weight"], 0.1,
                help="Adjusts the importance of Real Interest Rates in the formula"
            )
            st.session_state.weights["Forex_Reserves_weight"] = st.slider(
                "Forex Reserves Weight", 0.0, 2.0, st.session_state.weights["Forex_Reserves_weight"], 0.1,
                help="Adjusts the importance of foreign exchange reserves in the formula"
            )

    # Expert weights (only visible in expert mode)
    if calculation_mode == "Expert Indicators":
        with st.sidebar.expander("Expert Weights", expanded=True):
            st.session_state.weights["Debt_to_GDP_weight"] = st.slider(
                "Debt-to-GDP Weight", 0.0, 2.0, st.session_state.weights["Debt_to_GDP_weight"], 0.1,
                help="Adjusts the importance of debt-to-GDP ratio in the formula (lower is better)"
            )
            st.session_state.weights["Stability_weight"] = st.slider(
                "Economic Stability Weight", 0.0, 2.0, st.session_state.weights["Stability_weight"], 0.1,
                help="Adjusts the importance of economic stability metrics"
            )
    
    return calculation_mode, use_csv

def display_header(calculation_mode):
    """Display the application header"""
    header = st.container()
    header.title("BRICS Currency Framework Using Blockchain Technology")
    header.write(f"Calculation Mode: {calculation_mode}")
    header.write("""<div class='fixed-header'/>""", unsafe_allow_html=True)

    # Custom CSS for the sticky header
    st.markdown(
        """
        <style>
            div[data-testid="stVerticalBlock"] div:has(div.fixed-header) {
                # position: sticky;
                top: 2.875rem;
                background-color: white;
                z-index: 999;
                backdrop-filter: blur(3px);
            }
        </style>
        """,
        unsafe_allow_html=True
    )

def display_data_overview(df, calculation_mode):
    """Display data overview tab content"""
    st.write("### BRICS Currency Valuation Framework")

    st.write("Data are Fetched from World Bank API")
    column_order = ['Country Name', 'GDP', 'GDP Growth', 'Exports', 'Imports','Inflation CPI', 'Real Interest Rate', 'Forex Reserves', 'Debt to GDP']
    st.dataframe(df[column_order], hide_index=True)
    
    if 'replaced_values' in st.session_state and st.session_state.replaced_values:
        with st.expander("Missing Values Replaced"):
            st.write("### Missing Values Replaced with Mean:")
            for col, val in st.session_state.replaced_values.items():
                st.write(f"- **{col}**: Replaced missing values with {val:.2f}")

    # Determine which columns to display based on calculation mode
    if calculation_mode == "Basic Indicators":
        displayed_columns = ["Country", "Country Name", "Exports", "Imports", "BOT", "GDP", "SBC_Weight", "BRICS_Currency_Value", "Exchange_Rate_BC", "base currency"]
    elif calculation_mode == "Advanced Indicators":
        displayed_columns = ["Country Name", "Exports", "Imports", "BOT", "GDP", "Inflation CPI", "Real Interest Rate", "Forex Reserves", "SBC_Weight", "BRICS_Currency_Value", "Exchange_Rate_BC", "base currency"]
    else:  # Expert Indicators
        displayed_columns = ["Country Name", "Exports", "Imports", "BOT", "GDP", "GDP Growth", "Inflation CPI", "Real Interest Rate", "Forex Reserves", "Debt to GDP", "Stability Score", "SBC_Weight", "BRICS_Currency_Value", "Exchange_Rate_BC", "base currency"]
    
    
    # Display data with calculations
    st.dataframe(df[displayed_columns], hide_index=True)
    
    # Impact of weights on the calculation
    st.write("### Impact of Weights on Calculation")
    st.info("This section shows how the current weight settings affect the currency valuation compared to default weights (all at 1.0)")
    
    # Create baseline calculation with all weights at 1.0
    if st.session_state.baseline_currency_value == 0:
        st.session_state.baseline_currency_value = st.session_state.brics_currency_price
    
    st.metric(
        "Weight Impact", 
        f"{st.session_state.brics_currency_price:.4f}",
        delta=f"{(st.session_state.brics_currency_price - st.session_state.baseline_currency_value):.4f}",
        delta_color="normal"
    )
    
    # Display current weight settings in an organized way
    st.write("### Current Indicator Weights:")
    display_weight_metrics(calculation_mode)

def display_weight_metrics(calculation_mode):
    """Display the current weight metrics based on calculation mode"""
    # Display base weights for all modes
    base_cols = st.columns(4)
    with base_cols[0]:
        st.metric("GDP Weight", f"{st.session_state.weights['GDP_weight']:.1f}  x")
    with base_cols[1]:
        st.metric("BOT Weight", f"{st.session_state.weights['BOT_weight']:.1f}  x")
    with base_cols[2]:
        st.metric("Exports Weight", f"{st.session_state.weights['Exports_weight']:.1f}x")
    with base_cols[3]:
        st.metric("Imports Weight", f"{st.session_state.weights['Imports_weight']:.1f}x")

    # Advanced weights
    if calculation_mode in ["Advanced Indicators", "Expert Indicators"]:
        adv_cols = st.columns(3)
        with adv_cols[0]:
            st.metric("Inflation CPI Weight", f"{st.session_state.weights['Inflation_weight']:.1f}x")
        with adv_cols[1]:
            st.metric("Real Interest Rate Weight", f"{st.session_state.weights['Interest_Rate_weight']:.1f}x") 
        with adv_cols[2]:
            st.metric("Forex Reserves Weight", f"{st.session_state.weights['Forex_Reserves_weight']:.1f}x")

    # Expert weights
    if calculation_mode == "Expert Indicators":
        exp_cols = st.columns(2)
        with exp_cols[0]:
            st.metric("Debt-to-GDP Weight", f"{st.session_state.weights['Debt_to_GDP_weight']:.1f}x")
        with exp_cols[1]:
            st.metric("Stability Weight", f"{st.session_state.weights['Stability_weight']:.1f}x")

def display_scenario_analysis(df, calculation_mode):
    """Display scenario analysis tab content"""
    st.write("## Scenario Analysis")
    st.write("Manually adjust indicators to see the impact on BRICS currency valuation.")

    num_countries = len(df)
    cols = st.columns(num_countries)
    
    country_data = {}  # Store the updated values

    for i, country in enumerate(df["Country"]):
        with cols[i]:
            country_name = df.loc[df["Country"] == country, "Country Name"].values[0]
            st.write(f"### {country_name}")
            
            # Basic indicators
            exp = st.number_input(f"Exports (bn)", value=df.loc[df["Country"] == country, "Exports"].values[0], key=f"exp_{country}")
            imp = st.number_input(f"Imports (bn)", value=df.loc[df["Country"] == country, "Imports"].values[0], key=f"imp_{country}")
            gdp = st.number_input(f"GDP (bn)", value=df.loc[df["Country"] == country, "GDP"].values[0], key=f"gdp_{country}")
            
            # Store updated values
            country_data[country] = {"Exports": exp, "Imports": imp, "GDP": gdp}
            
            # Add more indicators for advanced and expert modes
            if calculation_mode in ["Advanced Indicators", "Expert Indicators"]:
                inf = st.number_input(f"Inflation CPI (%)", value=df.loc[df["Country"] == country, "Inflation CPI"].values[0], key=f"inf_{country}")
                int_rate = st.number_input(f"Real Interest Rate (%)", value=df.loc[df["Country"] == country, "Real Interest Rate"].values[0], key=f"int_{country}")
                forex = st.number_input(f"Forex Reserves (bn)", value=df.loc[df["Country"] == country, "Forex Reserves"].values[0], key=f"forex_{country}")
                
                # Add to country data
                country_data[country].update({"Inflation CPI": inf, "Real Interest Rate": int_rate, "Forex Reserves": forex})
                
                if calculation_mode == "Expert Indicators":
                    debt = st.number_input(f"Debt to GDP (%)", value=df.loc[df["Country"] == country, "Debt to GDP"].values[0], key=f"debt_{country}")
                    stability = st.number_input(f"Stability Score (0-1)", value=df.loc[df["Country"] == country, "Stability Score"].values[0], min_value=0.0, max_value=1.0, key=f"stab_{country}")
                    
                    # Add expert indicators to country data
                    country_data[country].update({"Debt to GDP": debt, "Stability Score": stability})
    
    # Button to recalculate with updated values
    if st.button("Recalculate BRICS Currency Values"):
        # Import in function to avoid circular import
        from calculations import recalculate_scenario
        
        updated_df, new_currency_price = recalculate_scenario(df.copy(), country_data, calculation_mode)
        
        # Show results
        st.success(f"Recalculation complete! New BRICS Currency Price: {new_currency_price:.4f}")
        
        # Determine which columns to display based on calculation mode
        if calculation_mode == "Basic Indicators":
            displayed_columns = ["Country", "Country Name", "Exports", "Imports", "BOT", "GDP", "SBC_Weight", "BRICS_Currency_Value", "Exchange_Rate_BC", "base currency"]
        elif calculation_mode == "Advanced Indicators":
            displayed_columns = ["Country Name", "Exports", "Imports", "BOT", "GDP", "Inflation CPI", "Real Interest Rate", "Forex Reserves", "SBC_Weight", "BRICS_Currency_Value", "Exchange_Rate_BC", "base currency"]
        else:  # Expert Indicators
            displayed_columns = ["Country Name", "Exports", "Imports", "BOT", "GDP", "GDP Growth", "Inflation CPI", "Real Interest Rate", "Forex Reserves", "Debt to GDP", "Stability Score", "SBC_Weight", "BRICS_Currency_Value", "Exchange_Rate_BC", "base currency"]
        
        st.dataframe(updated_df[displayed_columns], hide_index=True)
        
        # Show change from initial calculation
        st.metric(
            "Change from Base Scenario", 
            f"{new_currency_price:.4f}",
            delta=f"{(new_currency_price - st.session_state.brics_currency_price):.4f}",
            delta_color="normal"
        )
