import streamlit as st

def show_methodology():
    st.write("# Methodology & Justification")
    st.write("## Theoretical Foundation")
    st.write("""
    The BRICS Currency Framework is built on established economic principles that determine currency valuation 
    in international markets. The methodology incorporates various key indicators that influence 
    currency strength, stability, and international acceptance.
    Our approach draws from:
    - **Purchasing Power Parity Theory**: Considers relative economic output and price levels
    - **Balance of Payments Theory**: Examines trade flows and current account balances
    - **Interest Rate Parity**: Incorporates the effects of interest rate differentials
    - **Reserve Currency Requirements**: Recognizes the importance of stability and institutional strength
    """)
    st.write("## Core Calculation Logic")
    # Create tabs for different calculation modes
    mode_tabs = st.tabs(["Basic Indicators", "Advanced Indicators", "Expert Indicators"])
    with mode_tabs[0]:
        st.write("### Basic Indicators Formula")  
        st.write("""  
        The **Basic Indicators Formula** is derived from fundamental economic principles, particularly trade balance theory and GDP weighting.  
        **1. Understanding the Economic Factors**  
        A country’s currency strength is influenced by:  
        - **Balance of Trade (BOT)**: A trade surplus (Exports > Imports) increases demand for the domestic currency, leading to appreciation, while a trade deficit(Exports < Imports) causes depreciation. The BOT is calculated as:  
          **BOT = Exports - Imports**  
          - A positive BOT implies that the country exports more than it imports, boosting its currency value.
          - A negative BOT means the country imports more than it exports, weakening its currency.
        - **GDP Weighting**: Larger economies contribute more to the overall BRICS currency. The weight for each country is determined as:  
          **SBC Weight = (Country’s GDP) / (Sum of BRICS GDP)**  
          - Countries with higher GDP have a greater impact on the BRICS currency’s overall value.
        **2. Normalizing Trade Balance Impact**  
        To ensure the trade balance impact is measured relative to the size of the economy, we divide BOT by GDP:
          **Normalized BOT Impact = BOT / GDP**  
          - This ensures that a country’s trade surplus or deficit is compared fairly across different economies.
        **3. Adjusting Trade Impact Using a Weight Factor**  
        Since trade balance alone does not determine exchange rates, a weighting factor is introduced:
          **Weighted BOT Impact = (BOT / GDP) × W_BOT**  
          - **W_BOT** is an adjustable parameter that allows policymakers to control how much trade balance influences the BRICS currency valuation.
        **4. Ensuring a Non-Negative Scaling Factor**  
        To prevent the trade balance effect from reducing the currency value below zero, we add 1 to the factor:
          **BOT Adjustment Factor = 1 + (BOT / GDP × W_BOT)**  
          - This ensures that even countries with a trade deficit contribute positively to the currency but at a lower rate.
        **5. Applying GDP Weight for Currency Contribution**  
        The final formula integrates economic size and trade balance adjustment:
          **BRICS Currency Value = SBC Weight × (1 + (BOT / GDP) × W_BOT)**  
          - **SBC Weight** ensures the country’s influence is proportional to its economic power.
          - **BOT Adjustment Factor** accounts for trade surplus or deficit influence.
        **6. Final Code Representation**  
        ```python
        bot_factor = 1 + (df["BOT"] / df["GDP"]) * st.session_state.weights["BOT_weight"]
        df["BRICS_Currency_Value"] = df["SBC_Weight"] * bot_factor
        ```  
        - The **bot_factor** incorporates the trade balance impact with a scaling factor.
        - The **BRICS_Currency_Value** calculation ensures each country's contribution is weighted appropriately.
        """)
    with mode_tabs[1]:
        st.write("### Advanced Indicators Formula")  
        st.write("""  
        The **Advanced Indicators Formula** builds upon the Basic Indicators approach by incorporating additional macroeconomic factors that influence currency strength.These include inflation, interest rates, and foreign exchange reserves.
        **1. Balance of Trade Impact (Same as Basic Indicators)**  
        - **BOT Adjustment Factor**: (1 + (BOT / GDP) × W_BOT) ensures that trade surpluses contribute positively to the currency value.
        **2. Inflation Adjustment Factor**  
        - Inflation stability is crucial in maintaining a strong currency. Higher inflation erodes purchasing power, while very low inflation may indicate economicstagnation.
        - We adjust for inflation deviations from a target rate (2%) using:
          **Inflation Adjustment Factor = 1 - abs((Inflation - 2) / 10) × W_Inflation**  
          - Countries closer to the 2% target receive a higher score.
        **3. Interest Rate Influence**  
        - Higher interest rates attract foreign investment, increasing demand for the currency. The formula incorporates:
          **Interest Rate Factor = 1 + (Interest Rate / 100) × W_InterestRate**  
        **4. Foreign Exchange Reserves Contribution**  
        - Large forex reserves provide financial stability and help maintain exchange rate stability. We use:
          **Forex Reserves Factor = 1 + (Forex Reserves / (GDP × 10)) × W_ForexReserves**  
        **5. Final Calculation for BRICS Currency Value**  
        Integrating all factors:
        **BRICS Currency Value = SBC Weight × (1 + (BOT / GDP) × W_BOT) × (1 - abs((Inflation - 2) / 10) × W_Inflation) × (1 + (Interest Rate / 100) × W_InterestRate) ×(1 + (Forex Reserves / (GDP × 10)) × W_ForexReserves)**  
        **6. Final Code Representation**  
        ```python
        # Compute the BRICS Currency Value using Advanced Indicators
        df["BRICS_Currency_Value"] = df.apply(
            lambda row: row["SBC_Weight"] * (
                1 + (row["BOT"] / row["GDP"]) * st.session_state.weights["BOT_weight"]
            ) * (
                1 - abs((row["Inflation"] - 2) / 10) * st.session_state.weights["Inflation_weight"]
            ) * (
                1 + (row["Interest Rate"] / 100) * st.session_state.weights["Interest_Rate_weight"]
            ) * (
                1 + (row["Forex Reserves"] / (row["GDP"] * 10)) * st.session_state.weights["Forex_Reserves_weight"]
            ), 
            axis=1
        )
        ```
        - This formula integrates key macroeconomic factors to provide a more comprehensive measure of a country's contribution to the BRICS currency valuation.
        """)
    with mode_tabs[2]:
        st.write("### Expert Indicators Formula")  
        st.write("""  
        The **Expert Indicators Formula** expands upon the Advanced Indicators approach by incorporating additional economic stability factors, such as debt-to-GDP ratioand overall economic stability score.
        
        **1. Balance of Trade Impact (Same as Previous Models)**  
        - **BOT Adjustment Factor**: (1 + (BOT / GDP) × W_BOT) ensures that trade surpluses contribute positively to the currency value.
        
        **2. Inflation Adjustment Factor**  
        - Inflation stability is crucial in maintaining a strong currency. Higher inflation erodes purchasing power, while very low inflation may indicate economicstagnation.
        - We adjust for inflation deviations from a target rate (2%) using:  
          **Inflation Adjustment Factor = 1 - abs((Inflation - 2) / 10) × W_Inflation**  
          - Countries closer to the 2% target receive a higher score.
        
        **3. Interest Rate Influence**  
        - Higher interest rates attract foreign investment, increasing demand for the currency. The formula incorporates:  
          **Interest Rate Factor = 1 + (Interest Rate / 100) × W_InterestRate**  
        
        **4. Foreign Exchange Reserves Contribution**  
        - Large forex reserves provide financial stability and help maintain exchange rate stability. We use:  
          **Forex Reserves Factor = 1 + (Forex Reserves / (GDP × 10)) × W_ForexReserves**  
        
        **5. Debt-to-GDP Factor**  
        - A high debt-to-GDP ratio indicates financial instability and potential risk of default. We adjust for it using:  
          **Debt-to-GDP Factor = 1 - (Debt to GDP / 150) × W_DebtToGDP**  
          - Countries with lower debt receive a higher weight in currency valuation.
        
        **6. Economic Stability Score Contribution**  
        - This factor accounts for overall economic stability, incorporating multiple macroeconomic indicators. The adjustment is:  
          **Stability Factor = 1 + Stability Score × W_Stability**  
        
        **7. Final Calculation for BRICS Currency Value**  
        Integrating all factors:
        
        **BRICS Currency Value = SBC Weight × (1 + (BOT / GDP) × W_BOT) × (1 - abs((Inflation - 2) / 10) × W_Inflation) × (1 + (Interest Rate / 100) × W_InterestRate) ×(1 + (Forex Reserves / (GDP × 10)) × W_ForexReserves) × (1 - (Debt to GDP / 150) × W_DebtToGDP) × (1 + Stability Score × W_Stability)**  
        
        **8. Final Code Representation**  
        ```python
        # Compute the BRICS Currency Value using Expert Indicators
        
        df["BRICS_Currency_Value"] = df.apply(
            lambda row: row["SBC_Weight"] * (
                1 + (row["BOT"] / row["GDP"]) * st.session_state.weights["BOT_weight"]
            ) * (
                1 - abs((row["Inflation"] - 2) / 10) * st.session_state.weights["Inflation_weight"]
            ) * (
                1 + (row["Interest Rate"] / 100) * st.session_state.weights["Interest_Rate_weight"]
            ) * (
                1 + (row["Forex Reserves"] / (row["GDP"] * 10)) * st.session_state.weights["Forex_Reserves_weight"]
            ) * (
                1 - (row["Debt to GDP"] / 150) * st.session_state.weights["Debt_to_GDP_weight"]
            ) * (
                1 + row["Stability Score"] * st.session_state.weights["Stability_weight"]
            ), 
            axis=1
        )
        ```
        - This formula integrates key macroeconomic factors to provide the most comprehensive measure of a country's contribution to the BRICS currency valuation.
        """)
        
    st.write("## Weight Customization Rationale")
    st.write("""
    The framework allows user-defined weights for each indicator to:
    1. **Test Different Scenarios**: Simulate how changing priority on different economic factors affects valuation
    2. **Represent Different Perspectives**: Different stakeholders may prioritize different aspects:
       - Central banks may emphasize stability and reserves
       - Exporters may focus on trade balance effects
       - Investors might prioritize interest rates and growth
    3. **Account for Unique Conditions**: BRICS economies have diverse characteristics that might require 
       different emphasis depending on global economic conditions
    """)
    st.write("## Blockchain Integration Relevance")
    st.write("""
    While this framework focuses on the economic valuation aspects, blockchain technology would provide:
    1. **Transparency**: All calculations and weight adjustments are recorded immutably
    2. **Decentralization**: No single country can unilaterally manipulate the currency valuation
    3. **Smart Contract Governance**: Automated adjustment of weights based on predefined conditions
    4. **Consensus Mechanism**: Ensures all participating countries agree on calculation methodology
    The calculations performed in this framework would determine the initial and ongoing valuation 
    of the BRICS currency, which would then be implemented and maintained through blockchain infrastructure.
    """)
    st.write("## Limitations & Considerations")
    st.write("""
    This framework has certain limitations that should be acknowledged:
    1. **Simplification**: Real currency markets involve many additional factors not captured here
    2. **Historical Data**: The model doesn't incorporate extensive historical testing
    3. **Political Factors**: Non-economic influences on currency value aren't fully represented
    4. **Market Sentiment**: Speculative forces that can affect currency values aren't modeled
    5. **Implementation Challenges**: Practical issues of launching a new currency aren't addressed
    Future enhancements could include more sophisticated time-series analysis, geopolitical risk factors,
    and market sentiment indicators.
    """)
    # Add a reference section
    st.write("## References & Further Reading")
    st.write("""
    1. International Monetary Fund (IMF) - Special Drawing Rights Valuation Methodology
    2. Bank for International Settlements (BIS) - Global Currency Composition Reports
    3. World Bank - International Monetary System Analysis
    4. Economic research on reserve currency requirements and currency basket design
    """)