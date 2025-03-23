import streamlit as st
import pandas as pd
import time
from BCdatabase import get_user_notifications, mark_notification_as_read, get_unread_notification_count,get_notification_preferences, update_notification_preferences

# Import from our modules
from BCdatabase import init_db, login_user, register_user, get_user_balance, get_all_users
from BCtransaction_manager import (
    execute_transfer, request_money, respond_to_request, 
    get_transaction_history, get_transaction_details,
    get_pending_requests
)

# Initialize the database
init_db()

def notification_settings():
    """Display and manage notification settings"""
    if 'user_info' not in st.session_state:
        return
    
    user_id = st.session_state.user_info['user_id']
    
    st.header("Notification Settings")
    
    # Get current preferences
    prefs = get_notification_preferences(user_id)
    
    if not prefs:
        st.error("Could not load notification preferences.")
        return
    
    # Create form for notification settings
    with st.form("notification_settings_form"):
        st.subheader("Notification Types")
        
        receive_payment = st.toggle("Notify when I receive money", value=prefs['receive_payment_notify'] == 1)
        send_payment = st.toggle("Notify when I send money", value=prefs['send_payment_notify'] == 1)
        request_notify = st.toggle("Notify when someone requests money from me", value=prefs['request_notify'] == 1)
        request_response = st.toggle("Notify when someone responds to my money request", value=prefs['request_response_notify'] == 1)
        
        st.subheader("Notification Methods")
        
        push_enabled = st.toggle("Enable in-app notifications", value=prefs['push_enabled'] == 1)
        email_enabled = st.toggle("Enable email notifications", value=prefs['email_enabled'] == 1)
        
        if email_enabled:
            email = st.text_input("Email address for notifications", value=prefs['email'] or "")
        else:
            email = prefs['email'] or ""
        
        submit = st.form_submit_button("Save Settings")
        
        if submit:
            # Prepare the update
            new_prefs = {
                'receive_payment_notify': 1 if receive_payment else 0,
                'send_payment_notify': 1 if send_payment else 0,
                'request_notify': 1 if request_notify else 0,
                'request_response_notify': 1 if request_response else 0,
                'push_enabled': 1 if push_enabled else 0,
                'email_enabled': 1 if email_enabled else 0,
                'email': email if email_enabled else None
            }
            
            success, message = update_notification_preferences(user_id, new_prefs)
            
            if success:
                st.success("Notification settings updated successfully!")
            else:
                st.error(f"Error updating settings: {message}")


def main():
    st.set_page_config(
        page_title="BRICS Currency Transfer",
        page_icon="💱",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    if 'user_info' in st.session_state:
        display_notifications()
        setup_notification_checker()

def display_notifications():
    """Display the notification panel"""
    if 'user_info' not in st.session_state:
        return
    
    user_id = st.session_state.user_info['user_id']
    
    # Get unread notification count
    unread_count = get_unread_notification_count(user_id)
    
    # Create a container for notifications
    with st.sidebar:
        st.title("Notifications")
        
        # Add a refresh button
        if st.button("🔄 Refresh", key="refresh_notifications"):
            st.rerun()
        
        # Show notification count badge
        if unread_count > 0:
            st.markdown(f"""
            <div style="background-color:#ff4b4b; padding:10px; border-radius:5px; margin-bottom:10px; color:white;">
                <strong>You have {unread_count} new notification{'s' if unread_count > 1 else ''}!</strong>
            </div>
            """, unsafe_allow_html=True)
        
        # Get notifications
        show_read = st.toggle("Show read notifications", value=False)
        notifications = get_user_notifications(user_id, include_read=show_read)
        
        if not notifications:
            st.info("No notifications to display.")
        else:
            # Display notifications
            for notification in notifications:
                # Custom styling based on notification type and read status
                notification_style = ""
                if "Payment Received" in notification['title']:
                    notification_style = "border-left: 4px solid #4CAF50;"  # Green for received payments
                elif "Request" in notification['title']:
                    notification_style = "border-left: 4px solid #2196F3;"  # Blue for requests
                elif "Payment Sent" in notification['title']:
                    notification_style = "border-left: 4px solid #FFC107;"  # Yellow for sent payments
                
                # Add extra styling for unread notifications
                if notification['is_read'] == 0:
                    notification_style += "background-color: rgba(0, 0, 0, 0.05);"
                
                # Create a unique key for each notification expander
                with st.expander(f"{notification['title']} ({notification['created_at'][:16]})"):
                    st.markdown(notification['message'])
                    
                    if notification['transaction_id']:
                        st.caption(f"Transaction ID: {notification['transaction_id']}")
                    
                    if notification['is_read'] == 0:
                        if st.button("Mark as read", key=f"read_{notification['notification_id']}"):
                            mark_notification_as_read(notification['notification_id'])
                            st.success("Marked as read!")
                            time.sleep(0.5)
                            st.rerun()
def setup_notification_checker():
    """Setup automatic notification checking"""
    if 'user_info' not in st.session_state:
        return
    
    # Initialize notification state if needed
    if 'notification_state' not in st.session_state:
        st.session_state.notification_state = {
            'last_check_time': time.time(),
            'check_interval': 5,  # Check every 5 seconds
            'last_notification_count': 0,
            'notification_history': []
        }
    
    # This function will run periodically in the background
    def check_new_notifications():
        if 'user_info' not in st.session_state:
            return
        
        current_time = time.time()
        if current_time - st.session_state.notification_state['last_check_time'] > st.session_state.notification_state['check_interval']:
            user_id = st.session_state.user_info['user_id']
            unread_count = get_unread_notification_count(user_id)
            
            # If there are new notifications since last check
            if unread_count > st.session_state.notification_state['last_notification_count']:
                # Get the new notifications
                notifications = get_user_notifications(user_id, include_read=False)
                # Get only the ones we haven't seen yet
                new_notification_ids = [n['notification_id'] for n in notifications]
                previously_seen = st.session_state.notification_state['notification_history']
                new_notifications = [n for n in notifications if n['notification_id'] not in previously_seen]
                
                # Update our history
                st.session_state.notification_state['notification_history'] = new_notification_ids
                
                # Show toast for each new notification
                for notification in new_notifications:
                    st.toast(f"🔔 {notification['title']}: {notification['message'][:50]}...")
            
            # Update state
            st.session_state.notification_state['last_notification_count'] = unread_count
            st.session_state.notification_state['last_check_time'] = current_time
    
    # Inject JavaScript for real-time notification checking
    st.markdown("""
    <script>
        // Function to check for notifications every few seconds
        function checkNotifications() {
            window.parent.stApp.setComponentValue(
                'check_notifications_trigger', 
                Date.now()
            );
            setTimeout(checkNotifications, 5000);  // Check every 5 seconds
        }
        
        // Start the periodic checks
        setTimeout(checkNotifications, 2000);  // First check after 2 seconds
    </script>
    """, unsafe_allow_html=True)
    
    # This creates a "hidden" component that receives updates from JS
    check_trigger = st.empty()
    trigger_value = check_trigger.text_input("", key="check_notifications_trigger", label_visibility="collapsed")
    
    # When the trigger is updated, check for notifications
    if trigger_value:
        check_new_notifications()

def login_section():
    """Display login and registration options"""
    tab1, tab2 = st.tabs(["Login","Register"])
    with tab1:
        st.subheader("Login")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            success, result = login_user(username, password)
            if success:
                st.session_state.user_info = result
                st.success(f"Welcome back, {result['username']}!")
                st.rerun()
            else:
                st.error(result)
    with tab2:
        st.subheader("Register")
        new_username = st.text_input("Username", key="reg_username")
        new_password = st.text_input("Password", type="password", key="reg_password")
        country = st.selectbox("Country", ["Brazil", "Russia", "India", "China", "South Africa"])
        currency_mapping = {
        "Brazil": "BRL",
        "Russia": "RUB",
        "India": "INR",
        "China": "CNY",
        "South Africa": "ZAR"
        }
        if st.button("Register"):
            success, message = register_user(
            new_username,
            new_password,
            country,
            currency_mapping[country]
            )
            if success:
                st.success(message)
            else:
                st.error(message)

def check_for_new_transactions(user_id):
    """Check if there are new transactions since last check"""
    if 'last_transaction_check' not in st.session_state:
        st.session_state.last_transaction_check = {
            'timestamp': time.time(),
            'transaction_ids': []
        }
    
    # Get current transactions
    current_transactions = get_transaction_history(user_id)
    current_transaction_ids = [tx['transaction_id'] for tx in current_transactions]
    
    # Compare with previously known transactions
    known_transaction_ids = st.session_state.last_transaction_check['transaction_ids']
    
    # Find new transactions
    new_transaction_ids = [tx_id for tx_id in current_transaction_ids if tx_id not in known_transaction_ids]
    new_transactions = [tx for tx in current_transactions if tx['transaction_id'] in new_transaction_ids]
    
    # Update state
    st.session_state.last_transaction_check['timestamp'] = time.time()
    st.session_state.last_transaction_check['transaction_ids'] = current_transaction_ids
    
    return new_transactions

# First, let's update the transfer_interface function in the second file (paste-2.txt)
def transfer_interface():
    """Display the transfer interface for logged-in users with BRICS value support"""
    user_info = st.session_state.user_info
    
    if 'last_notification_check' not in st.session_state:
        st.session_state.last_notification_check = time.time()
        
    # Check every 30 seconds (configurable)
    current_time = time.time()
    if current_time - st.session_state.last_notification_check > 30:
        unread_count = get_unread_notification_count(user_info['user_id'])
        if unread_count > 0:
            st.toast(f"You have {unread_count} new notification{'s' if unread_count > 1 else ''}")
        st.session_state.last_notification_check = current_time

    st.subheader(f"Welcome, {user_info['username']} ({user_info['currency']})")
    
    # Show current balance with BRICS equivalent
    balance = get_user_balance(user_info['user_id'], user_info['currency']) 
    
    # Currency mapping for exchange rate lookups
    currency_mapping = {
        "CNY": "CN", "INR": "IN", "RUB": "RU", "BRL": "BR", "ZAR": "ZA"
    }
    user_currency_code = currency_mapping.get(user_info['currency'])
    
    # Display both local and BRICS balances
    if 'ex_rates' in st.session_state and user_currency_code in st.session_state.ex_rates:
        # Convert to BRICS value using exchange rates
        brics_value = balance / st.session_state.ex_rates[user_currency_code]
        
        # Create two columns for the balances
        col1, col2 = st.columns(2)
        with col1:
            rbalance = round(balance,2)
            st.metric("Local Currency Balance", f"{rbalance} {user_info['currency']}")
        with col2:
            st.metric("BRICS Balance", f"{round(brics_value, 2)} BRICS")
    else:
        st.info(f"Your current balance: {balance} {user_info['currency']}")
        st.warning("Exchange rates not available. Please visit the Data Overview tab to load rates.")
    
    # Create tabs for transfer options
    transfer_tab, request_tab, history_tab, verify_tab, notify_settings_tab = st.tabs(
        ["Send Money", "Request Money", "Transaction History", "Verify Transaction", "Notification Settings"]
    )
    
    with transfer_tab:
        st.subheader("Send Money")
        # Get all users (excluding current user)
        all_users = [u for u in get_all_users() if u['user_id'] != user_info['user_id']]
        if all_users:
            receiver = st.selectbox(
                "Select Recipient", 
                options=all_users,
                format_func=lambda x: f"{x['username']} ({x['country']} - {x['currency']})"
            )
            
            # Add toggle for currency type
            currency_type = st.radio(
                "Send in:",
                options=["Local Currency", "BRICS"],
                horizontal=True,
                key="send_currency_type"
            )
            
            if currency_type == "Local Currency":
                # Local currency input
                amount = st.number_input("Amount to Send (Local Currency)", min_value=0.01, value=10.0, step=1.0, key="send_local")
                
                # Show BRICS equivalent of input amount
                if 'ex_rates' in st.session_state:
                    sender_code = currency_mapping.get(user_info['currency'])
                    if sender_code in st.session_state.ex_rates:
                        brics_amount = amount / st.session_state.ex_rates[sender_code]
                        st.info(f"BRICS Equivalent: {round(brics_amount, 2)} BRICS")
            else:
                # BRICS input
                brics_amount = st.number_input("Amount to Send (BRICS)", min_value=0.01, value=1.0, step=0.1, key="send_brics")
                
                # Show local currency equivalent
                if 'ex_rates' in st.session_state:
                    sender_code = currency_mapping.get(user_info['currency'])
                    if sender_code in st.session_state.ex_rates:
                        amount = brics_amount * st.session_state.ex_rates[sender_code]
                        st.info(f"Local Equivalent: {round(amount, 2)} {user_info['currency']}")
            
            description = st.text_input("Description (optional)", "")
            
            # Display conversion preview with both currencies
            if 'ex_rates' in st.session_state:
                try:
                    sender_code = currency_mapping.get(user_info['currency'])
                    receiver_code = currency_mapping.get(receiver['currency'])
                    
                    if sender_code in st.session_state.ex_rates and receiver_code in st.session_state.ex_rates:
                        # Convert via BRICS common unit
                        if currency_type == "Local Currency":
                            # Already calculated brics_amount above
                            converted_amount = brics_amount * st.session_state.ex_rates[receiver_code]
                        else:
                            # Already set brics_amount directly
                            converted_amount = brics_amount * st.session_state.ex_rates[receiver_code]
                        
                        # Show conversion details
                        st.write("### Conversion Details")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("You Send", f"{round(amount, 2)} {user_info['currency']}")
                        with col2:
                            st.metric("BRICS Value", f"{round(brics_amount, 2)} BRICS")
                        with col3:
                            st.metric("Recipient Gets", f"{round(converted_amount, 2)} {receiver['currency']}")
                        
                        # Show exchange rates used
                        st.caption(f"Exchange Rates: 1 BRICS = {st.session_state.ex_rates[sender_code]} {user_info['currency']} | 1 BRICS = {st.session_state.ex_rates[receiver_code]} {receiver['currency']}")
                        
                        if st.button("Send Money"):
                            # Calculate the actual amount in local currency for balance check
                            local_amount_to_send = amount
                            
                            if local_amount_to_send > balance:
                                st.error("Insufficient funds for this transfer.")
                            else:
                                success, message = execute_transfer(
                                    user_info['user_id'], 
                                    receiver['user_id'], 
                                    amount if currency_type == "Local Currency" else brics_amount,
                                description, is_brics_amount=(currency_type == "BRICS")
                                )
                                if success:
                                    st.success(message)
                                    st.rerun()  # Refresh balance
                                else:
                                    st.error(message)
                    else:
                        st.error(f"Exchange rates not available for {user_info['currency']} or {receiver['currency']}")
                except Exception as e:
                    st.error(f"Error calculating conversion: {str(e)}")
            else:
                st.error("Exchange rates not available. Please visit the Data Overview tab first.")
        else:
            st.info("No other users available for transfer.")
            
    with request_tab:
        st.subheader("Request Money")
        # Get all users (excluding current user)
        all_users = [u for u in get_all_users() if u['user_id'] != user_info['user_id']]
        if all_users:
            payer = st.selectbox(
                "Request From", 
                options=all_users,
                format_func=lambda x: f"{x['username']} ({x['country']} - {x['currency']})",
                key="request_user"
            )
            
            # Add toggle for currency type in request
            request_currency_type = st.radio(
                "Request in:",
                options=["Their Currency", "BRICS", "Your Currency"],
                horizontal=True,
                key="request_currency_type"
            )
            
            payer_code = currency_mapping.get(payer['currency'])
            requester_code = currency_mapping.get(user_info['currency'])
            
            if request_currency_type == "Their Currency":
                # Request in payer's currency
                req_amount = st.number_input("Amount to Request (in their currency)", 
                                            min_value=0.01, value=10.0, step=1.0, key="req_their")
                
                # Calculate BRICS and your currency equivalents
                if 'ex_rates' in st.session_state and payer_code in st.session_state.ex_rates and requester_code in st.session_state.ex_rates:
                    brics_amount = req_amount / st.session_state.ex_rates[payer_code]
                    your_amount = brics_amount * st.session_state.ex_rates[requester_code]
                    st.info(f"BRICS Equivalent: {round(brics_amount, 2)} BRICS | Your Currency: {round(your_amount, 2)} {user_info['currency']}")
            
            elif request_currency_type == "BRICS":
                # Request in BRICS
                brics_amount = st.number_input("Amount to Request (BRICS)", 
                                              min_value=0.01, value=1.0, step=0.1, key="req_brics")
                
                # Calculate payer and your currency equivalents
                if 'ex_rates' in st.session_state and payer_code in st.session_state.ex_rates and requester_code in st.session_state.ex_rates:
                    req_amount = brics_amount * st.session_state.ex_rates[payer_code]
                    your_amount = brics_amount * st.session_state.ex_rates[requester_code]
                    st.info(f"Their Currency: {round(req_amount, 2)} {payer['currency']} | Your Currency: {round(your_amount, 2)} {user_info['currency']}")
            
            else:  # Your Currency
                # Request in requester's currency
                your_amount = st.number_input("Amount to Request (in your currency)", 
                                            min_value=0.01, value=10.0, step=1.0, key="req_your")
                
                # Calculate BRICS and payer currency equivalents
                if 'ex_rates' in st.session_state and payer_code in st.session_state.ex_rates and requester_code in st.session_state.ex_rates:
                    brics_amount = your_amount / st.session_state.ex_rates[requester_code]
                    req_amount = brics_amount * st.session_state.ex_rates[payer_code]
                    st.info(f"BRICS Equivalent: {round(brics_amount, 2)} BRICS | Their Currency: {round(req_amount, 2)} {payer['currency']}")
            
            # Show conversion details for request
            if 'ex_rates' in st.session_state and payer_code in st.session_state.ex_rates and requester_code in st.session_state.ex_rates:
                st.write("### Request Details")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("They'll Pay", f"{round(req_amount, 2)} {payer['currency']}")
                with col2:
                    st.metric("BRICS Value", f"{round(brics_amount, 2)} BRICS")
                with col3:
                    st.metric("You'll Receive", f"{round(your_amount, 2)} {user_info['currency']}")
            
            req_description = st.text_input("Request Description", "")
            
            if st.button("Send Request"):
                # For the request, we need to use the payer's currency value
                # since the database expects amount in sender's currency
                success, message = request_money(
                    user_info['user_id'],
                    payer['user_id'],
                    req_amount,  # Always use the payer's currency amount
                    req_description
                )
                if success:
                    st.success(message)
                else:
                    st.error(message)
        else:
            st.info("No other users available to request money from.")
    
    # The rest of the function (history_tab, verify_tab, pending_requests) remains unchanged
    with history_tab:
        st.subheader("Transaction History")
        
        # Add a refresh button
        if st.button("🔄 Refresh Transactions"):
            # Check for new transactions
            new_transactions = check_for_new_transactions(user_info['user_id'])
            if new_transactions:
                st.success(f"Found {len(new_transactions)} new transaction(s)!")
            st.rerun()
        
        # Get transactions
        transactions = get_transaction_history(user_info['user_id'])
        
        # Initialize transaction cache if not exists
        if 'transaction_cache' not in st.session_state:
            st.session_state.transaction_cache = []
        
        # Check for new transactions compared to cache
        new_tx_ids = [tx['transaction_id'] for tx in transactions if tx['transaction_id'] not in 
                     [cached_tx['transaction_id'] for cached_tx in st.session_state.transaction_cache]]
        
        if new_tx_ids and st.session_state.transaction_cache:  # Only alert if cache is not empty (not first load)
            st.success(f"You have {len(new_tx_ids)} new transaction(s)!")
        
        # Update cache
        st.session_state.transaction_cache = transactions
        
        # Display transactions
        if transactions:
            for tx in transactions:
                # Calculate BRICS value for this transaction
                brics_value = None
                if 'ex_rates' in st.session_state:
                    sender_code = currency_mapping.get(tx['sender_currency'])
                    if sender_code in st.session_state.ex_rates:
                        brics_value = tx['amount_sent'] / st.session_state.ex_rates[sender_code]
                
                # Create expander with BRICS value included
                title = f"{tx['type'].title()}: {tx['amount_sent']} {tx['sender_currency']}"
                if brics_value:
                    title += f" ({round(brics_value, 2)} BRICS)"
                title += f" → {tx['amount_received']} {tx['receiver_currency']}"
                
                with st.expander(f"{title} ({tx['created_at'][:16]})"):
                    st.write(f"From: {tx['sender_name']}")
                    st.write(f"To: {tx['receiver_name']}")
                    if tx['description']:
                        st.write(f"Description: {tx['description']}")
                    
                    # Display BRICS values in more detail
                    if brics_value:
                        st.write("### Value in BRICS")
                        st.write(f"BRICS Value: {round(brics_value, 2)} BRICS")
                    
                    st.write(f"Status: {tx['status'].title()}")
                    st.write(f"Blockchain Status: {tx['blockchain_status'].title()}")
                    st.write(f"Transaction ID: {tx['transaction_id']}")
        else:
            st.info("No transaction history yet.")
            
    with verify_tab:
        st.subheader("Verify Transaction")
        tx_id = st.text_input("Enter Transaction ID")
        if tx_id and st.button("Verify"):
            tx_details = get_transaction_details(tx_id)
            if tx_details:
                # Add BRICS values to the transaction details
                if 'ex_rates' in st.session_state:
                    sender_code = currency_mapping.get(tx_details['sender_currency'])
                    if sender_code in st.session_state.ex_rates:
                        tx_details['brics_value'] = round(tx_details['amount_sent'] / st.session_state.ex_rates[sender_code], 2)
                
                # Display the enhanced transaction details
                st.json(tx_details)
                if tx_details['blockchain_verified']:
                    st.success(tx_details['blockchain_message'])
                else:
                    st.warning(tx_details['blockchain_message'])
            else:
                st.error("Transaction not found.")
    
    with notify_settings_tab:
        notification_settings()

    # Show pending requests with BRICS values
    pending_requests = get_pending_requests(user_info['user_id'])
    if pending_requests:
        st.subheader("Pending Requests")
        for req in pending_requests:
            # Calculate BRICS value for this request
            brics_value = None
            if 'ex_rates' in st.session_state:
                sender_code = currency_mapping.get(req['sender_currency'])
                if sender_code in st.session_state.ex_rates:
                    brics_value = req['amount_sent'] / st.session_state.ex_rates[sender_code]
            
            # Title with BRICS value
            title = f"Request from {req['requester_name']}: {req['amount_sent']} {req['sender_currency']}"
            if brics_value:
                title += f" ({round(brics_value, 2)} BRICS)"
            
            with st.expander(title):
                st.write(f"Description: {req['description'] or 'No description'}")
                
                # Show BRICS values in detail if available
                if brics_value:
                    st.write(f"BRICS Value: {round(brics_value, 2)} BRICS")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Approve", key=f"approve_{req['transaction_id']}"):
                        success, msg = respond_to_request(req['transaction_id'], "approve")
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                with col2:
                    if st.button("Reject", key=f"reject_{req['transaction_id']}"):
                        success, msg = respond_to_request(req['transaction_id'], "reject")
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
    
    # Logout button
    if st.button("Logout"):
        del st.session_state.user_info
        st.success("Logged out successfully.")
        st.rerun()
        
def display_transfer_tab():
    """Display the transfer tab in the Streamlit interface"""
    st.header("BRICS Currency Transfer")
    
    # Check if user is logged in
    if 'user_info' not in st.session_state:
        login_section()
    else:
        # User is logged in, show transfer interface
        transfer_interface()

if __name__ == "__main__":
    main()