import requests
import pandas as pd
import os
import streamlit as st

# Initialize session state if not already set
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
    st.session_state.total_gdp = 0
    st.session_state.brics_currency_price = 0

# Sidebar: User input to determine data source
st.sidebar.title("BRICS Currency Dashboard")
use_csv = st.sidebar.radio("Select Data Source:", ["Use API", "Upload CSV"])

if use_csv == "Upload CSV":
    uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])
    if uploaded_file:
        st.session_state.df = pd.read_csv(uploaded_file)
        st.success("CSV File Loaded Successfully!")
    else:
        st.warning("Please upload a CSV file.")
else:
    # Fetch data from World Bank API
    base_url = "http://api.worldbank.org/v2/country/{}/indicator/{}?format=json&date=2023"
    countries = ["CN", "IN", "RU", "BR", "ZA"]
    indicators = {"Exports": "NE.EXP.GNFS.CD", "Imports": "NE.IMP.GNFS.CD", "GDP": "NY.GDP.MKTP.CD"}

    data = []
    total_gdp = 0
    for country in countries:
        row = {"Country": country}
        for key, indicator in indicators.items():
            response = requests.get(base_url.format(country, indicator))
            if response.status_code == 200:
                json_data = response.json()
                try:
                    value = json_data[1][0]['value'] if json_data[1] else None
                except (KeyError, IndexError, TypeError):
                    value = None
            else:
                value = None
            row[key] = value
        row["BOT"] = (row["Exports"] or 0) - (row["Imports"] or 0)
        total_gdp += row["GDP"] or 0
        data.append(row)
    
    st.session_state.df = pd.DataFrame(data)
    st.session_state.df.to_csv("BRICS_Trade_GDP_Data.csv", index=False)
    st.success("Data fetched from API and saved successfully!")



# Ensure there is data before proceeding
if st.session_state.df.empty:
    st.error("No data available. Please upload a CSV file or fetch data from the API.")
else:
    df = st.session_state.df
    df["Exports"] = df["Exports"].fillna(0) / 1e9  # Convert to billions
    df["Imports"] = df["Imports"].fillna(0) / 1e9  # Convert to billions

    df["GDP"] = df["GDP"].fillna(0) / 1e9  # Convert to billions
    st.header("BRICS Currency Framework Using BlockChain Technology") 
    st.write("Fetched Data From API")
    st.dataframe(df)
    df["BOT"] = df["Exports"] - df["Imports"]
    

    # Calculate total GDP
    st.session_state.total_gdp = df["GDP"].sum()
    
    # Calculate the SBC weight and BRICS Currency Value
    df["SBC_Weight"] = df["GDP"] / st.session_state.total_gdp if st.session_state.total_gdp > 0 else 0
    df["BRICS_Currency_Value"] = df.apply(lambda row: row["SBC_Weight"] * (1 + (row["BOT"] / row["GDP"] if row["GDP"] > 0 else 1)), axis=1)
    st.session_state.brics_currency_price = df["BRICS_Currency_Value"].sum()
    df["Exchange_Rate_BC"] = df.apply(lambda row: 1 / row["BRICS_Currency_Value"] if row["BRICS_Currency_Value"] > 0 else None, axis=1)
    
    df.to_csv("BRICS_Trade_GDP_Data.csv", index=False)
    
    # Create tabs for data visualization

    tab1, tab2 = st.tabs(["Data Overview", "Scenario Analysis & Forecasting"])
    
    with tab1:
        st.write("### Indicators Used")
        st.markdown("Total Import")
        st.markdown("Total Export")
        st.markdown("Balance of Trade")
        st.markdown("GDP")
        st.success("Data successfully saved to BRICS_Trade_GDP_Data.csv")
        st.write("### BRICS Currency Valuation Framework")
        st.dataframe(df)
        st.write("## Overall BRICS Currency Price:", st.session_state.brics_currency_price)
    
    with tab2:
        st.write("## Scenario Analysis")
        st.write("Manually adjust indicators to see the impact on BRICS currency valuation.")

        # Compact Layout using Columns
        num_countries = len(df)
        cols = st.columns(num_countries)  # Create a column for each country

        for i, country in enumerate(df["Country"]):
            with cols[i]:  # Assign each country to a separate column
                st.write(f"### {country}")
                exp = st.number_input(f"Exports", value=df.loc[df["Country"] == country, "Exports"].values[0] or 0, key=f"exp_{country}")
                imp = st.number_input(f"Imports", value=df.loc[df["Country"] == country, "Imports"].values[0] or 0, key=f"imp_{country}")
                gdp = st.number_input(f"GDP", value=df.loc[df["Country"] == country, "GDP"].values[0] or 0, key=f"gdp_{country}")
                
                # Update values in DataFrame
                df.loc[df["Country"] == country, ["Exports", "Imports", "GDP"]] = [exp, imp, gdp]

        # Recalculate values based on user input
        df["BOT"] = df["Exports"] - df["Imports"]
        st.session_state.total_gdp = df["GDP"].sum()
        df["SBC_Weight"] = df["GDP"] / st.session_state.total_gdp
        df["BRICS_Currency_Value"] = df.apply(lambda row: row["SBC_Weight"] * (1 + (row["BOT"] / row["GDP"] if row["GDP"] > 0 else 1)), axis=1)
        df["Exchange_Rate_BC"] = df.apply(lambda row: 1 / row["BRICS_Currency_Value"] if row["BRICS_Currency_Value"] > 0 else None, axis=1)
        st.session_state.df = df

        st.write("## Updated BRICS Currency Valuation")
        st.dataframe(df)
        st.write("## Updated Overall BRICS Currency Price:", df["BRICS_Currency_Value"].sum())
        st.write("## Updated Exchange Rates")
        st.dataframe(df[["Country", "Exchange_Rate_BC"]])
