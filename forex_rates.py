import requests
import streamlit as st
import pandas as pd

API_KEY = "02e3c1142f8d4846a5e12dda1c7590e1"
API_URL = f"https://api.currencyfreaks.com/latest?apikey={API_KEY}"

def fetch_forex_rates():
    """Fetches live forex exchange rates from CurrencyFreaks API."""
    try:
        response = requests.get(API_URL)
        data = response.json()
        return data["rates"]
    except Exception as e:
        st.error(f"Error fetching forex rates: {e}")
        return None

def calculate_brics_forex_rates(brics_currency_value, forex_rates):
    """Calculates BRICS currency exchange rates against major currencies and adds interpretation."""
    major_currencies = ["USD", "EUR", "GBP", "JPY", "AUD"]
    brics_exchange_rates = []

    for currency in major_currencies:
        if currency in forex_rates:
            exchange_rate = brics_currency_value / float(forex_rates[currency])
            interpretation = f"1 BRICS Currency = {exchange_rate:.4f} {currency}"
            brics_exchange_rates.append({
                "Currency": currency,
                "Exchange Rate": round(exchange_rate, 6),
                "Interpretation": interpretation
            })
    
    return pd.DataFrame(brics_exchange_rates)

def calculate_brics_nation_forex(df, forex_rates):
    """Calculates exchange rates of individual BRICS nations against major currencies with interpretation."""
    major_currencies = ["USD", "EUR", "GBP", "JPY", "AUD"]
    
    # Dictionary mapping BRICS nations to their respective currency codes
    brics_currency_mapping = {
        "China": "CNY",
        "India": "INR",
        "Russia": "RUB",
        "Brazil": "BRL",
        "South Africa": "ZAR"
    }

    brics_nation_rates = []
    
    for country, currency_code in brics_currency_mapping.items():
        if currency_code in forex_rates:
            row = {"Country": country, "Base Currency": currency_code}
            interpretation_text = []

            for currency in major_currencies:
                if currency in forex_rates:
                    exchange_rate = round(float(forex_rates[currency]) / float(forex_rates[currency_code]), 6)
                    row[currency] = exchange_rate
                    interpretation_text.append(f"1 {currency_code} = {exchange_rate} {currency}")
            
            row["Interpretation"] = " | ".join(interpretation_text)  # Combine all interpretations into a single column
            brics_nation_rates.append(row)
    
    return pd.DataFrame(brics_nation_rates)

def display_forex_tables(df):
    """Displays the BRICS exchange rates and BRICS nations' currency conversions."""
    
    if "BRICS_Currency_Value" not in df.columns:
        st.error("BRICS_Currency_Value column not found in dataset!")
        return
    
    # Get BRICS Currency Value (You may change sum if needed)
    brics_currency_value = df["BRICS_Currency_Value"].sum()

    # Fetch live forex rates
    forex_rates = fetch_forex_rates()
    
    if forex_rates:
        # Table 1: BRICS Calculated Currency Exchange Rates with Interpretation
        brics_forex_df = calculate_brics_forex_rates(brics_currency_value, forex_rates)
        st.subheader("BRICS Calculated Currency Exchange Rates")
        st.dataframe(brics_forex_df, hide_index=True)

        # Table 2: BRICS Nation Currencies to Major Forex Pairs with Interpretation
        brics_nation_forex_df = calculate_brics_nation_forex(df, forex_rates)
        st.subheader("BRICS Nations' Currency Exchange Rates with Major Pairs")
        st.dataframe(brics_nation_forex_df, hide_index=True)
