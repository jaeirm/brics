import streamlit as st
import requests

API_URL = "http://127.0.0.1:5000"  # Flask API URL

st.title("BRICS Transfer Framework - CBDC Monitoring")

# Fetch and display account balances
st.header("CBDC Account Balances")
countries = ["India", "China", "Russia", "Brazil", "South Africa"]
balances = {}

for country in countries:
    response = requests.get(f"{API_URL}/balance/{country}")
    if response.status_code == 200:
        data = response.json()
        balances[country] = f"{data['balance']} {data['currency']}"
    else:
        balances[country] = "Error fetching data"

st.write(balances)

# Perform a transfer
st.header("CBDC Transfer Simulation")
from_country = st.selectbox("From Country", countries)
to_country = st.selectbox("To Country", [c for c in countries if c != from_country])
amount = st.number_input("Amount", min_value=1.0, step=0.1)

if st.button("Transfer"):
    response = requests.post(f"{API_URL}/transfer", json={
        "sender": from_country + "_CBDC",  # Fix key name
        "receiver": to_country + "_CBDC",  # Fix key name
        "amount": amount,
        "currency": "BRICS"
    })
    if response.status_code == 200:
        st.success("Transaction Successful!")
    else:
        st.error(response.json().get("error", "Transaction Failed!"))

# Display Transactions
st.header("Transaction History")
response = requests.get(f"{API_URL}/transactions")
if response.status_code == 200:
    transactions = response.json()
    st.table(transactions)
else:
    st.error("Failed to fetch transactions")
