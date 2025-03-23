import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

@st.cache_data
def fetch_data_from_api():
    """Fetches data from the World Bank API with fallback to previous year."""
    base_url = "http://api.worldbank.org/v2/country/{}/indicator/{}?format=json&date={}"
    countries = ["CN", "IN", "RU", "BR", "ZA"]
    indicators = {
        "Exports": "NE.EXP.GNFS.CD",
        "Imports": "NE.IMP.GNFS.CD",
        "GDP": "NY.GDP.MKTP.CD",
        "Inflation CPI": "FP.CPI.TOTL.ZG",
        "Real Interest Rate": "FR.INR.RINR",
        "Forex Reserves": "FI.RES.TOTL.CD",
        "Debt to GDP": "GC.DOD.TOTL.GD.ZS",
        "GDP Growth": "NY.GDP.MKTP.KD.ZG"
    }

    data = []
    
    for country in countries:
        row = {"Country": country}
        
        for key, indicator in indicators.items():
            value = None
            
            # Try fetching data for 2023, fallback to 2022
            for year in ["2023", "2022", "2021", "2020"]:
                api_url = base_url.format(country, indicator, year)
                response = requests.get(api_url)

                if response.status_code == 200:
                    json_data = response.json()
                    try:
                        if json_data[1]:
                            value = json_data[1][0]['value']

                            # If value is found, store and break the loop
                            if value is not None:
                                break  
                            
                    except (KeyError, IndexError, TypeError):
                        value = None  # Ensure value is None if any exception occurs

            # Store the extracted value in the dictionary
            row[key] = value
            
            # Debugging Output
            print(f"{country} - {key}: {value}")
            
        data.append(row)
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Map country codes to full names
    country_mapping = {
        "CN": "China",
        "IN": "India",
        "RU": "Russia",
        "BR": "Brazil",
        "ZA": "South Africa"
    }
    df["Country Name"] = df["Country"].map(country_mapping)

    print("Final DataFrame:")
    print(df)

    df.to_csv("BRICS_Trade_GDP_Data.csv", index=False)
    return df

def preprocess_data(df):
    """Preprocess the data - handle missing values and convert units."""
    # Create a copy to avoid modifying the original DataFrame
    df = df.copy()

    # Dictionary to store replaced values for logging
    replaced_values = {}
    
    # Ensure "Debt to GDP" exists in the dataset before processing
    if "Debt to GDP" in df.columns:
        # Replace China's missing Debt to GDP with 84.38
        china_mask = (df["Country"] == "CN") & (df["Debt to GDP"].isnull())
        if china_mask.any():
            df.loc[china_mask, "Debt to GDP"] = 84.38
            replaced_values["China - Debt to GDP"] = 84.38  # Store for logging

        # Replace India's missing Debt to GDP with 81.59
        india_mask = (df["Country"] == "IN") & (df["Debt to GDP"].isnull())
        if india_mask.any():
            df.loc[india_mask, "Debt to GDP"] = 81.59
            replaced_values["India - Debt to GDP"] = 81.59  # Store for logging

    # Fill other missing values with the column mean (excluding "Country" columns)
    for col in df.columns:
        if col not in ["Country", "Country Name"] and df[col].isnull().any():
            mean_value = df[col].mean(skipna=True)
            df[col].fillna(mean_value, inplace=True)
            replaced_values[f"Mean - {col}"] = mean_value  # Store for logging

    # Convert to billions for better readability
    df["Exports"] = df["Exports"] / 1e9
    df["Imports"] = df["Imports"] / 1e9
    df["GDP"] = df["GDP"] / 1e9
    df["Forex Reserves"] = df["Forex Reserves"] / 1e9  # Convert to billions for consistency

    # Calculate stability score (used in Expert mode)
    if "GDP Growth" in df.columns:
        # Normalize GDP growth (higher is better, but capped at reasonable range)
        df["Normalized GDP Growth"] = df["GDP Growth"].clip(0, 10) / 10
        
        # Normalize Inflation CPI (lower is better, with optimal range around 2-3%)
        df["Normalized Inflation CPI"] = 1 - (abs(df["Inflation CPI"] - 2.5) / 10).clip(0, 1)
        
        # Calculate stability score
        df["Stability Score"] = (df["Normalized GDP Growth"] + df["Normalized Inflation CPI"]) / 2
    else:
        # If GDP growth data isn't available, use a placeholder
        df["Stability Score"] = 0.5  # Neutral score
    
    # Add base currency names
    df["base currency"] = ["Yuan", "Rupee", "Ruble", "Real", "Rand"]
    
    # Store replaced values in session state for access in display_data_overview
    st.session_state.replaced_values = replaced_values
    
    return df, replaced_values

def load_data(use_csv):
    """Load data based on user selection"""
    if use_csv == "Upload CSV":
        uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            st.toast("CSV File Loaded Successfully!")
        else:
            st.warning("Please upload a CSV file.")
            return pd.DataFrame()
    else:
        df = fetch_data_from_api()
        st.toast("Data fetched from API and saved successfully!")
    
    # Ensure data is available before proceeding
    if df.empty:
        st.error("No data available. Please upload a CSV file or fetch data from the API.")
        return df
    
    # Preprocess the data
    df, replaced_values = preprocess_data(df)
    
    # Store in session state
    st.session_state.df = df
    return df
    

def save_data(df):
    """Save the dataframe to CSV"""
    df.to_csv("BRICS_Trade_GDP_Data.csv", index=False)
