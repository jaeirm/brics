import requests
import pandas as pd
import streamlit as st
import plotly.express as px

# Initialize session state if not already set
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()
    st.session_state.total_gdp = 0
    st.session_state.brics_currency_price = 0

# Sidebar: User input to determine data source and calculation mode
st.sidebar.title("BRICS Currency Dashboard")
use_csv = st.sidebar.radio("Select Data Source:", ["Use API", "Upload CSV"])
calculation_mode = st.sidebar.radio("Select Calculation Mode:", ["Basic Indicators", "Advanced Indicators"])

@st.cache_data
def fetch_data_from_api():
    """Fetches data from the World Bank API."""
    base_url = "http://api.worldbank.org/v2/country/{}/indicator/{}?format=json&date=2023"
    countries = ["CN", "IN", "RU", "BR", "ZA"]

    indicators = {
        "Exports": "NE.EXP.GNFS.CD",
        "Imports": "NE.IMP.GNFS.CD",
        "GDP": "NY.GDP.MKTP.CD",
        "Inflation": "FP.CPI.TOTL.ZG",
        "Interest Rate": "FR.INR.RINR",
        "Forex Reserves": "FI.RES.TOTL.CD",
    }

    data = []
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
        data.append(row)

    df = pd.DataFrame(data)
    df.to_csv("BRICS_Trade_GDP_Data.csv", index=False)
    return df

# Load data based on user selection
if use_csv == "Upload CSV":
    uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])
    if uploaded_file:
        st.session_state.df = pd.read_csv(uploaded_file)
        st.success("CSV File Loaded Successfully!")
    else:
        st.warning("Please upload a CSV file.")
else:
    st.session_state.df = fetch_data_from_api()
    st.success("Data fetched from API and saved successfully!")

# Ensure data is available before proceeding
if st.session_state.df.empty:
    st.error("No data available. Please upload a CSV file or fetch data from the API.")
else:
    df = st.session_state.df.copy()  # Ensure changes do not persist across multiple runs

    # Fill missing values with the column mean
    replaced_values = {}
    for col in df.columns[1:]:  # Skip Country column
        if df[col].isnull().any():
            mean_value = df[col].mean()
            df[col].fillna(mean_value, inplace=True)
            replaced_values[col] = mean_value  # Store replaced values

    # Convert to billions for better readability
    df["Exports"] = df["Exports"] / 1e9
    df["Imports"] = df["Imports"] / 1e9
    df["GDP"] = df["GDP"] / 1e9
    df["BOT"] = df["Exports"] - df["Imports"]

    # Calculate total GDP
    st.session_state.total_gdp = df["GDP"].sum()

    # Calculate BRICS Currency Value dynamically based on the selected mode
    if calculation_mode == "Basic Indicators":
        df["SBC_Weight"] = df["GDP"] / st.session_state.total_gdp
        df["BRICS_Currency_Value"] = df["SBC_Weight"] * (1 + (df["BOT"] / df["GDP"]))
        displayed_columns = ["Country", "Exports", "Imports", "BOT", "GDP", "SBC_Weight", "BRICS_Currency_Value"]
    else:  # Advanced Mode
        df["SBC_Weight"] = df["GDP"] / st.session_state.total_gdp
        df["BRICS_Currency_Value"] = df.apply(
            lambda row: row["SBC_Weight"] * (1 + (row["BOT"] / row["GDP"])) *
            (1 + (row["Inflation"] / 100)) * (1 + (row["Interest Rate"] / 100)) *
            (1 + (row["Forex Reserves"] / 1e12)), axis=1
        )
        displayed_columns = ["Country", "Exports", "Imports", "BOT", "GDP", "Inflation", "Interest Rate", "Forex Reserves", "SBC_Weight", "BRICS_Currency_Value"]

    # Calculate Exchange Rate based on BRICS currency value
    df["Exchange_Rate_BC"] = df["BRICS_Currency_Value"].apply(lambda x: 1 / x if x > 0 else None)
    displayed_columns.append("Exchange_Rate_BC")

    # Store final currency price in session state
    st.session_state.brics_currency_price = df["BRICS_Currency_Value"].sum()

    # Save the updated dataset
    df.to_csv("BRICS_Trade_GDP_Data.csv", index=False)

    # Display data
    st.header("BRICS Currency Framework Using Blockchain Technology")
    st.subheader(f"Calculation Mode: {calculation_mode}")
    st.dataframe(df[displayed_columns])  # Display only selected indicators based on mode

    # Display Replaced Missing Values
    if replaced_values:
        st.write("### Missing Values Replaced with Mean:")
        for col, val in replaced_values.items():
            st.write(f"- **{col}**: Replaced missing values with {val:.2f}")

    # Visualizations
    st.write("## Visualizations")

    # GDP Contribution Pie Chart
    fig_gdp = px.pie(df, names="Country", values="GDP", title="GDP Contribution of BRICS Nations")
    st.plotly_chart(fig_gdp)

    # Balance of Trade Bar Chart
    fig_bot = px.bar(df, x="Country", y="BOT", title="Balance of Trade (Exports - Imports)", color="BOT")
    st.plotly_chart(fig_bot)

    # Tabs for Scenario Analysis
    tab1, tab2 = st.tabs(["Data Overview", "Scenario Analysis & Forecasting"])

    with tab1:
        st.write("### BRICS Currency Valuation Framework")
        st.dataframe(df[displayed_columns])
        st.write("## Overall BRICS Currency Price:", st.session_state.brics_currency_price)

    with tab2:
        st.write("## Scenario Analysis")
        st.write("Manually adjust indicators to see the impact on BRICS currency valuation.")

        num_countries = len(df)
        cols = st.columns(num_countries)

        for i, country in enumerate(df["Country"]):
            with cols[i]:
                st.write(f"### {country}")
                exp = st.number_input(f"Exports", value=df.loc[df["Country"] == country, "Exports"].values[0], key=f"exp_{country}")
                imp = st.number_input(f"Imports", value=df.loc[df["Country"] == country, "Imports"].values[0], key=f"imp_{country}")
                gdp = st.number_input(f"GDP", value=df.loc[df["Country"] == country, "GDP"].values[0], key=f"gdp_{country}")

                df.loc[df["Country"] == country, ["Exports", "Imports", "GDP"]] = [exp, imp, gdp]

        st.write("## Updated BRICS Currency Valuation")
        st.dataframe(df[displayed_columns])
        st.write("## Updated Overall BRICS Currency Price:", df["BRICS_Currency_Value"].sum())
        st.write("## Updated Exchange Rates")
        st.dataframe(df[["Country", "Exchange_Rate_BC"]])
