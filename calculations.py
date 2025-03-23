import streamlit as st
import pandas as pd

def calculate_currency_values(df, calculation_mode):
    """Calculate BRICS currency values based on the selected mode"""
    
    # Apply weights to exports and imports before calculating BOT
    df["Weighted_Exports"] = df["Exports"] * st.session_state.weights["Exports_weight"]
    df["Weighted_Imports"] = df["Imports"] * st.session_state.weights["Imports_weight"]
    df["BOT"] = df["Weighted_Exports"] - df["Weighted_Imports"]
    
    # Apply a penalty for negative BOT (trade deficit)
    df["BOT_Penalty"] = 1 - (df["BOT"].apply(lambda x: max(-x, 0)) / df["GDP"]) * st.session_state.weights.get("BOT_Penalty_weight", 0.1)

    # Calculate total GDP with weight applied
    weighted_gdp = df["GDP"] * st.session_state.weights["GDP_weight"]
    st.session_state.total_gdp = weighted_gdp.sum()

    # Calculate SBC Weight (share of BRICS GDP)
    df["SBC_Weight"] = weighted_gdp / st.session_state.total_gdp

    # Basic mode calculation
    if calculation_mode == "Basic Indicators":
        bot_factor = 1 + (df["BOT"] / df["GDP"]) * st.session_state.weights["BOT_weight"]
        df["BRICS_Currency_Value"] = df["SBC_Weight"] * bot_factor * df["BOT_Penalty"]

    
    # Advanced mode calculation    
    elif calculation_mode == "Advanced Indicators":
        df["BRICS_Currency_Value"] = df.apply(
            lambda row: row["SBC_Weight"] * (
                1 + (row["BOT"] / row["GDP"]) * st.session_state.weights["BOT_weight"]
            ) * row["BOT_Penalty"] * (
                (1 - abs((row["Inflation CPI"] - 2) / 10) * st.session_state.weights["Inflation_weight"])
            ) * (
                (1 + (row["Real Interest Rate"] / 100) * st.session_state.weights["Interest_Rate_weight"])
            ) * (
                (1 + (row["Forex Reserves"] / (row["GDP"] * 10)) * st.session_state.weights["Forex_Reserves_weight"])
            ), 
            axis=1
        )
    
    # Expert mode calculation
    else:  # Expert Indicators
        df["BRICS_Currency_Value"] = df.apply(
            lambda row: row["SBC_Weight"] * (
                1 + (row["BOT"] / row["GDP"]) * st.session_state.weights["BOT_weight"]
            ) * row["BOT_Penalty"] * (
                (1 - abs((row["Inflation CPI"] - 2) / 10) * st.session_state.weights["Inflation_weight"])
            ) * (
                (1 + (row["Real Interest Rate"] / 100) * st.session_state.weights["Interest_Rate_weight"])
            ) * (
                (1 + (row["Forex Reserves"] / (row["GDP"] * 10)) * st.session_state.weights["Forex_Reserves_weight"])
            ) * (
                (1 - (row["Debt to GDP"] / 150) * st.session_state.weights["Debt_to_GDP_weight"])
            ) * (
                (1 + row["Stability Score"] * st.session_state.weights["Stability_weight"])
            ), 
            axis=1
        )

    # Calculate Exchange Rate based on BRICS currency value
    df["Exchange_Rate_BC"] = df["BRICS_Currency_Value"].apply(lambda x: 1 / x if x > 0 else None)

    # Store final currency price in session state
    st.session_state.brics_currency_price = df["BRICS_Currency_Value"].sum()
    
    return df

def recalculate_scenario(df, country_data, calculation_mode):
    """Recalculate BRICS currency values based on scenario analysis inputs"""
    
    # Update dataframe with user inputs
    for country, values in country_data.items():
        for key, value in values.items():
            df.loc[df["Country"] == country, key] = value

    # Update weighted values based on user inputs
    df["Weighted_Exports"] = df["Exports"] * st.session_state.weights["Exports_weight"]
    df["Weighted_Imports"] = df["Imports"] * st.session_state.weights["Imports_weight"]
    df["BOT"] = df["Weighted_Exports"] - df["Weighted_Imports"]

    # Apply penalty for negative BOT
    df["BOT_Penalty"] = 1 - (df["BOT"].apply(lambda x: max(-x, 0)) / df["GDP"]) * st.session_state.weights.get("BOT_Penalty_weight", 0.1)

    # Recalculate weighted GDP and SBC weights
    weighted_gdp = df["GDP"] * st.session_state.weights["GDP_weight"]
    total_weighted_gdp = weighted_gdp.sum()
    df["SBC_Weight"] = weighted_gdp / total_weighted_gdp

    # Recalculate BRICS currency values based on mode
    if calculation_mode == "Basic Indicators":
        bot_factor = 1 + (df["BOT"] / df["GDP"]) * st.session_state.weights["BOT_weight"]
        df["BRICS_Currency_Value"] = df["SBC_Weight"] * bot_factor * df["BOT_Penalty"]
    
    elif calculation_mode == "Advanced Indicators":
        df["BRICS_Currency_Value"] = df.apply(
            lambda row: row["SBC_Weight"] * (
                1 + (row["BOT"] / row["GDP"]) * st.session_state.weights["BOT_weight"]
            ) * row["BOT_Penalty"] * (
                (1 - abs((row["Inflation CPI"] - 2) / 10) * st.session_state.weights["Inflation CPI_weight"])
            ) * (
                (1 + (row["Real Interest Rate"] / 100) * st.session_state.weights["Interest_Rate_weight"])
            ) * (
                (1 + (row["Forex Reserves"] / (row["GDP"] * 10)) * st.session_state.weights["Forex_Reserves_weight"])
            ), 
            axis=1
        )
    
    else:  # Expert Indicators
        df["BRICS_Currency_Value"] = df.apply(
            lambda row: row["SBC_Weight"] * (
                1 + (row["BOT"] / row["GDP"]) * st.session_state.weights["BOT_weight"]
            ) * row["BOT_Penalty"] * (
                (1 - abs((row["Inflation CPI"] - 2) / 10) * st.session_state.weights["Inflation CPI_weight"])
            ) * (
                (1 + (row["Real Interest Rate"] / 100) * st.session_state.weights["Interest_Rate_weight"])
            ) * (
                (1 + (row["Forex Reserves"] / (row["GDP"] * 10)) * st.session_state.weights["Forex_Reserves_weight"])
            ) * (
                (1 - (row["Debt to GDP"] / 150) * st.session_state.weights["Debt_to_GDP_weight"])
            ) * (
                (1 + row["Stability Score"] * st.session_state.weights["Stability_weight"])
            ), 
            axis=1
        )
    
    # Update exchange rates
    df["Exchange_Rate_BC"] = df["BRICS_Currency_Value"].apply(lambda x: 1 / x if x > 0 else None)

    # Calculate new currency price
    new_currency_price = df["BRICS_Currency_Value"].sum()

    return df, new_currency_price
