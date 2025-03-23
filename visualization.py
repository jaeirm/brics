import streamlit as st
import pandas as pd
import plotly.express as px

def visualize_data(df, calculation_mode):
    """Generate visualizations for GDP contribution, Balance of Trade, and weight impact analysis."""
    st.write("## Visualizations")
    
    # GDP Contribution Pie Chart
    fig_gdp = px.pie(df, names="Country", values="GDP", title="GDP Contribution of BRICS Nations")
    st.plotly_chart(fig_gdp)
    
    # Balance of Trade Bar Chart
    fig_bot = px.bar(df, x="Country", y="BOT", title="Balance of Trade (Weighted Exports - Weighted Imports)", color="BOT")
    st.plotly_chart(fig_bot)
    
    # Weight Impact Visualization
    st.write("## Weight Impact Analysis")
    # Create a baseline calculation with all weights at 1.0
    baseline_values = {}
    for country in df["Country"]:
        gdp_val = df.loc[df["Country"] == country, "GDP"].values[0]
        sbc_baseline_weight = gdp_val / df["GDP"].sum()
        bot_baseline = df.loc[df["Country"] == country, "Exports"].values[0] - df.loc[df["Country"] == country, "Imports"].values[0]
        bot_ratio = bot_baseline / gdp_val
        
        if calculation_mode == "Basic Indicators":
            baseline_values[country] = sbc_baseline_weight * (1 + bot_ratio)
        else:
            Inflation = df.loc[df["Country"] == country, "Inflation CPI"].values[0] / 100
            interest_rate = df.loc[df["Country"] == country, "Real Interest Rate"].values[0] / 100
            forex = df.loc[df["Country"] == country, "Forex Reserves"].values[0] / 1e12
            baseline_values[country] = sbc_baseline_weight * (1 + bot_ratio) * (1 + Inflation) * (1 + interest_rate) * (1 + forex)
    
    # Compare current values with baseline
    impact_data = []
    for country in df["Country"]:
        current_value = df.loc[df["Country"] == country, "BRICS_Currency_Value"].values[0]
        baseline = baseline_values[country]
        percent_change = ((current_value / baseline) - 1) * 100
        impact_data.append({
            "Country": country,
            "Baseline Value": baseline,
            "Current Value": current_value,
            "Percent Change": percent_change
        })
    
    impact_df = pd.DataFrame(impact_data)
    st.dataframe(impact_df, hide_index=True)
    
    # Visualization of weight impact
    fig_impact = px.bar(
        impact_df, x="Country", y="Percent Change", 
        title="Impact of Weight Adjustments on Currency Values (%)",
        color="Percent Change", text="Percent Change"
    )
    fig_impact.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    st.plotly_chart(fig_impact)
    
    # Weight sensitivity analysis
    st.write("## Weight Sensitivity Analysis")
    
    weight_names = ["GDP", "BOT", "Exports", "Imports"]
    if calculation_mode == "Advanced Indicators":
        weight_names.extend(["Inflation", "Interest_Rate", "Forex_Reserves"])
        
    fig_sensitivity = px.bar(
        x=weight_names,
        y=[st.session_state.weights[f"{w}_weight"] for w in weight_names],
        title="Current Weight Settings",
        labels={"x": "Indicator", "y": "Weight Value"}
    )
    st.plotly_chart(fig_sensitivity)
