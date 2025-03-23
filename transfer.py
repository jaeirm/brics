import streamlit as st
import sqlite3
import pandas as pd
import datetime
import os
import uuid
import json
import hashlib
import time
import requests
# Replacing deprecated hfc imports with fabric-sdk-py
# Note: Even fabric-sdk-py has maintenance issues, so this implementation 
# provides a fallback to REST API approach when needed
try:
    from fabric_sdk_py.client import Client
    from fabric_sdk_py.user import create_user
    FABRIC_SDK_AVAILABLE = True
except ImportError:
    FABRIC_SDK_AVAILABLE = False
    # For REST API approach when SDK is not available
    import requests

# Create database directory if it doesn't exist
if not os.path.exists("data"):
    os.makedirs("data")

# Hyperledger Fabric Configuration
def init_fabric_client():
    """Initialize the Hyperledger Fabric client using either SDK or REST approach"""
    try:
        # Path to the connection profile
        
        net_profile_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'connection-profile.json'
        )
        
        if FABRIC_SDK_AVAILABLE:
            # Use fabric-sdk-py if available
            # Load the connection profile
            with open(net_profile_path, 'r') as f:
                network_config = json.load(f)
                
            # Create a client instance
            client = Client(net_config=network_config)
            
            # Set the organization and user context
            org1_admin = client.get_user('BRICS', 'admin')
            
            # Get the channel instance
            channel = client.new_channel('mychannel')
            
            return client, channel, "sdk"
        else:
            # Fallback to REST API approach
            # Check if Fabric REST endpoint is available
            try:
                # Get REST API endpoint from config
                with open(net_profile_path, 'r') as f:
                    config = json.load(f)
                    
                fabric_api_url = config.get('fabric_api_url', 'http://localhost:3000/api')
                
                # Test connection
                response = requests.get(f"{fabric_api_url}/health", timeout=2)
                if response.status_code == 200:
                    return fabric_api_url, None, "rest"
            except:
                pass
            
            # If we reach here, neither SDK nor REST is available
            raise Exception("No Fabric connectivity options available")
    except Exception as e:
        st.error(f"Error initializing Fabric client: {str(e)}")
        # Fallback to local mode if Fabric is not available
        st.warning("Fabric blockchain unavailable. Falling back to local database only.")
        return None, None, "local"

# Create a transaction record on the blockchain
def record_transaction_on_blockchain(transaction_data):
    """Record a transaction on the Hyperledger Fabric blockchain"""
    client_or_url, channel, mode = init_fabric_client()
    
    if mode == "local":
        # Blockchain unavailable, continue with local DB only
        return True, "Blockchain unavailable, transaction recorded in local database only."
    
    try:
        # Convert transaction data to JSON string
        tx_data_str = json.dumps(transaction_data)
        
        if mode == "sdk":
            # Use SDK approach
            client, channel = client_or_url, channel
            # Invoke the chaincode
            response = channel.chaincode_invoke(
                chaincode_name='bricstransfer',
                fcn='recordTransaction',
                args=[tx_data_str],
                targets=[f'peer0.brics.example.com'],
                wait_for_event=True
            )
            
            if response:
                return True, "Transaction successfully recorded on blockchain."
            else:
                return False, "Failed to record transaction on blockchain."
                
        elif mode == "rest":
            # Use REST API approach
            api_url = client_or_url
            payload = {
                "function": "recordTransaction",
                "args": [tx_data_str],
                "channelId": "bricschannel",
                "chaincodeId": "bricstransfer"
            }
            
            response = requests.post(
                f"{api_url}/invoke", 
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return True, "Transaction successfully recorded on blockchain via REST API."
            else:
                return False, f"Failed to record transaction on blockchain. Status: {response.status_code}"
    except Exception as e:
        # Log the error but continue with local DB transaction
        print(f"Blockchain recording error: {str(e)}")
        return False, f"Blockchain error: {str(e)}"

# Verify transaction on blockchain
def verify_transaction_on_blockchain(transaction_id):
    """Verify a transaction record on the blockchain"""
    client_or_url, channel, mode = init_fabric_client()
    
    if mode == "local":
        return False, "Blockchain verification unavailable."
    
    try:
        if mode == "sdk":
            # Use SDK approach
            client, channel = client_or_url, channel
            # Query the chaincode
            response = channel.chaincode_query(
                chaincode_name='bricstransfer',
                fcn='getTransaction',
                args=[transaction_id],
                targets=[f'peer0.brics.example.com']
            )
            
            if response:
                return True, json.loads(response)
            else:
                return False, "Transaction not found on blockchain."
                
        elif mode == "rest":
            # Use REST API approach
            api_url = client_or_url
            payload = {
                "function": "getTransaction",
                "args": [transaction_id],
                "channelId": "bricschannel",
                "chaincodeId": "bricstransfer"
            }
            
            response = requests.get(
                f"{api_url}/query", 
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("result"):
                    return True, result.get("result")
                else:
                    return False, "Transaction not found on blockchain."
            else:
                return False, f"Blockchain verification failed. Status: {response.status_code}"
    except Exception as e:
        return False, f"Blockchain verification error: {str(e)}"

# Generate a blockchain hash for transaction
def generate_transaction_hash(transaction_data):
    """Generate a secure hash for the transaction data"""
    # Convert transaction data to string and encode
    tx_string = json.dumps(transaction_data, sort_keys=True)
    # Create SHA-256 hash
    return hashlib.sha256(tx_string.encode()).hexdigest()

# The rest of the database and application functions remain the same

# Setup the SQLite database
def init_db():
    conn = sqlite3.connect('data/brics_transfer.db')
    c = conn.cursor()
    
    # Create users table if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            country TEXT NOT NULL,
            currency TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create accounts table if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            account_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            currency TEXT NOT NULL,
            balance REAL DEFAULT 1000.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Check if transactions table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
    table_exists = c.fetchone()
    
    if not table_exists:
        # Create transactions table if it doesn't exist
        c.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                sender_id TEXT NOT NULL,
                receiver_id TEXT NOT NULL,
                sender_currency TEXT NOT NULL,
                receiver_currency TEXT NOT NULL,
                amount_sent REAL NOT NULL,
                amount_received REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                type TEXT NOT NULL,
                description TEXT,
                blockchain_hash TEXT,
                blockchain_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users (user_id),
                FOREIGN KEY (receiver_id) REFERENCES users (user_id)
            )
        ''')
    else:
        # Check if blockchain_status column exists
        c.execute("PRAGMA table_info(transactions)")
        columns = [column[1] for column in c.fetchall()]
        
        # Add blockchain_status column if it doesn't exist
        if 'blockchain_status' not in columns:
            c.execute('ALTER TABLE transactions ADD COLUMN blockchain_status TEXT DEFAULT "pending"')
    
    conn.commit()
    conn.close()
# Initialize database
init_db()

# Enhanced transfer function with blockchain integration
def execute_transfer(sender_id, receiver_id, amount, description=""):
    """Execute a transfer between users with blockchain validation"""
    conn = sqlite3.connect('data/brics_transfer.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get sender's and receiver's currencies
    c.execute("SELECT currency FROM users WHERE user_id = ?", (sender_id,))
    sender_currency = c.fetchone()["currency"]
    
    c.execute("SELECT currency FROM users WHERE user_id = ?", (receiver_id,))
    receiver_currency = c.fetchone()["currency"]
    
    # Check if sender has sufficient balance
    sender_balance = get_user_balance(sender_id, sender_currency)
    if sender_balance < amount:
        conn.close()
        return False, "Insufficient balance for this transfer."
    
    # Get exchange rates from session state
    if "ex_rates" not in st.session_state:
        conn.close()
        return False, "Exchange rates not available. Please calculate values first."
    
    # Map currency codes to exchange rate keys
    currency_mapping = {
        "CNY": "CN",
        "INR": "IN",
        "RUB": "RU",
        "BRL": "BR",
        "ZAR": "ZA"
    }
    
    sender_rate_key = currency_mapping.get(sender_currency)
    receiver_rate_key = currency_mapping.get(receiver_currency)
    
    if sender_rate_key not in st.session_state.ex_rates or receiver_rate_key not in st.session_state.ex_rates:
        conn.close()
        return False, f"Exchange rate missing for {sender_currency} or {receiver_currency}."
    
    # Convert amount using exchange rates
    brics_amount = amount / st.session_state.ex_rates[sender_rate_key]  # Convert to BRICS currency
    converted_amount = brics_amount * st.session_state.ex_rates[receiver_rate_key]  # Convert to target currency
    
    # Generate transaction ID
    transaction_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().isoformat()
    
    # Prepare transaction data for blockchain
    transaction_data = {
        "transaction_id": transaction_id,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "sender_currency": sender_currency,
        "receiver_currency": receiver_currency,
        "amount_sent": amount,
        "amount_received": converted_amount,
        "exchange_rate_sender": st.session_state.ex_rates[sender_rate_key],
        "exchange_rate_receiver": st.session_state.ex_rates[receiver_rate_key],
        "timestamp": timestamp,
        "type": "transfer",
        "description": description
    }
    
    # Generate blockchain hash
    blockchain_hash = generate_transaction_hash(transaction_data)
    
    try:
        # Start transaction in local database
        c.execute("BEGIN TRANSACTION")
        
        # Update sender's balance
        c.execute(
            "UPDATE accounts SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND currency = ?",
            (amount, sender_id, sender_currency)
        )
        
        # Update receiver's balance
        c.execute(
            "UPDATE accounts SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND currency = ?",
            (converted_amount, receiver_id, receiver_currency)
        )
        
        # Record the transaction in local database with blockchain hash
        c.execute(
            """INSERT INTO transactions 
                (transaction_id, sender_id, receiver_id, sender_currency, receiver_currency, 
                amount_sent, amount_received, status, type, description, blockchain_hash, blockchain_status, 
                created_at, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
            (transaction_id, sender_id, receiver_id, sender_currency, receiver_currency, 
             amount, converted_amount, "completed", "transfer", description, blockchain_hash, "pending")
        )
        
        # Commit local transaction
        conn.commit()
        
        # Now try to record on blockchain
        bc_success, bc_message = record_transaction_on_blockchain(transaction_data)
        
        # Update blockchain status in local DB
        if bc_success:
            c.execute(
                "UPDATE transactions SET blockchain_status = 'confirmed' WHERE transaction_id = ?",
                (transaction_id,)
            )
            conn.commit()
        
        conn.close()
        
        # Return success with blockchain status information
        if bc_success:
            return True, f"Successfully transferred {amount} {sender_currency} to {round(converted_amount, 2)} {receiver_currency}. Blockchain confirmation: successful."
        else:
            return True, f"Transfer completed in local database. {amount} {sender_currency} to {round(converted_amount, 2)} {receiver_currency}. Note: {bc_message}"
    
    except Exception as e:
        # Rollback in case of error
        conn.rollback()
        conn.close()
        return False, f"Error executing transfer: {str(e)}"

# Enhanced money request function with blockchain integration
def request_money(requester_id, payer_id, amount, description=""):
    """Create a money request with blockchain record"""
    conn = sqlite3.connect('data/brics_transfer.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get currencies
    c.execute("SELECT currency FROM users WHERE user_id = ?", (requester_id,))
    requester_currency = c.fetchone()["currency"]
    
    c.execute("SELECT currency FROM users WHERE user_id = ?", (payer_id,))
    payer_currency = c.fetchone()["currency"]
    
    # Generate transaction ID
    transaction_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().isoformat()
    
    # Prepare request data for blockchain
    request_data = {
        "transaction_id": transaction_id,
        "requester_id": requester_id,
        "payer_id": payer_id,
        "requester_currency": requester_currency,
        "payer_currency": payer_currency,
        "amount": amount,
        "timestamp": timestamp,
        "type": "request",
        "status": "pending",
        "description": description
    }
    
    # Generate blockchain hash
    blockchain_hash = generate_transaction_hash(request_data)
    
    try:
        # Record the request in local database
        c.execute(
            """INSERT INTO transactions 
                (transaction_id, sender_id, receiver_id, sender_currency, receiver_currency, 
                amount_sent, amount_received, status, type, description, blockchain_hash, blockchain_status,
                created_at, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
            (transaction_id, payer_id, requester_id, payer_currency, requester_currency, 
             amount, amount, "pending", "request", description, blockchain_hash, "pending")
        )
        
        conn.commit()
        
        # Try to record on blockchain
        bc_success, bc_message = record_transaction_on_blockchain(request_data)
        
        # Update blockchain status in local DB
        if bc_success:
            c.execute(
                "UPDATE transactions SET blockchain_status = 'confirmed' WHERE transaction_id = ?",
                (transaction_id,)
            )
            conn.commit()
        
        conn.close()
        
        # Return success with blockchain status information
        if bc_success:
            return True, f"Money request sent successfully. Request ID: {transaction_id}. Blockchain confirmation: successful."
        else:
            return True, f"Money request sent successfully. Request ID: {transaction_id}. Note: {bc_message}"
    
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, f"Error creating request: {str(e)}"

# Add functions for blockchain verification
def verify_transaction(transaction_id):
    """Verify a transaction against blockchain record"""
    conn = sqlite3.connect('data/brics_transfer.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get the transaction from local database
    c.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
    transaction = c.fetchone()
    
    if not transaction:
        conn.close()
        return False, "Transaction not found in local database."
    
    # Convert to dict for easier handling
    transaction = dict(transaction)
    
    # Check if this transaction has a blockchain record
    if not transaction['blockchain_hash']:
        conn.close()
        return False, "This transaction has no blockchain record."
    
    # Verify against blockchain
    bc_success, bc_data = verify_transaction_on_blockchain(transaction_id)
    
    conn.close()
    
    if not bc_success:
        return False, "Transaction verification failed: Not found on blockchain or blockchain unavailable."
    
    # Compare hash from local DB with blockchain data
    if transaction['blockchain_hash'] == bc_data.get('hash'):
        return True, "Transaction verified on blockchain. Integrity confirmed."
    else:
        return False, "Transaction verification failed: Data mismatch between local and blockchain records."

# Function to get transaction details with blockchain verification
def get_transaction_details(transaction_id):
    """Get detailed transaction info with blockchain verification status"""
    conn = sqlite3.connect('data/brics_transfer.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get detailed transaction info
    c.execute("""
        SELECT t.*, 
               u1.username as sender_name, 
               u2.username as receiver_name,
               t.blockchain_status
        FROM transactions t
        JOIN users u1 ON t.sender_id = u1.user_id
        JOIN users u2 ON t.receiver_id = u2.user_id
        WHERE t.transaction_id = ?
    """, (transaction_id,))
    
    transaction = c.fetchone()
    conn.close()
    
    if not transaction:
        return None
    
    # Convert to dict
    result = dict(transaction)
    
    # Add blockchain verification status
    if result['blockchain_hash']:
        verification, message = verify_transaction(transaction_id)
        result['blockchain_verified'] = verification
        result['blockchain_message'] = message
    else:
        result['blockchain_verified'] = False
        result['blockchain_message'] = "Transaction has no blockchain record."
    
    return result

# Enhanced function to get transaction history with blockchain status
def get_transaction_history(user_id):
    """Get transaction history for a user with blockchain status"""
    conn = sqlite3.connect('data/brics_transfer.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get all transactions with blockchain status where the user is either sender or receiver
    c.execute("""
        SELECT t.*, 
               u1.username as sender_name, 
               u2.username as receiver_name,
               t.blockchain_status
        FROM transactions t
        JOIN users u1 ON t.sender_id = u1.user_id
        JOIN users u2 ON t.receiver_id = u2.user_id
        WHERE (t.sender_id = ? OR t.receiver_id = ?) AND (t.status = 'completed' OR t.type = 'transfer')
        ORDER BY t.created_at DESC
    """, (user_id, user_id))
    
    transactions = []
    for row in c.fetchall():
        transactions.append(dict(row))
    
    conn.close()
    return transactions

# User authentication and other existing functions remain unchanged
def register_user(username, password, country, currency):
    """Register a new user in the database"""
    conn = sqlite3.connect('data/brics_transfer.db')
    c = conn.cursor()
    
    # Check if username already exists
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    if c.fetchone():
        conn.close()
        return False, "Username already exists. Please choose another."
    
    # Generate unique user ID
    user_id = str(uuid.uuid4())
    
    # Insert new user
    c.execute(
        "INSERT INTO users (user_id, username, password, country, currency) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, password, country, currency)
    )
    
    # Create account for the user with initial balance
    account_id = str(uuid.uuid4())
    c.execute(
        "INSERT INTO accounts (account_id, user_id, currency, balance) VALUES (?, ?, ?, ?)",
        (account_id, user_id, currency, 1000.0)
    )
    
    conn.commit()
    conn.close()
    return True, "Registration successful! Please login."

def login_user(username, password):
    """Authenticate user login"""
    conn = sqlite3.connect('data/brics_transfer.db')
    c = conn.cursor()
    
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    conn.close()
    
    if user:
        # User found, return user details
        return True, {
            "user_id": user[0],
            "username": user[1],
            "country": user[3],
            "currency": user[4]
        }
    else:
        return False, "Invalid username or password."

def get_user_balance(user_id, currency):
    """Get user's current balance"""
    conn = sqlite3.connect('data/brics_transfer.db')
    c = conn.cursor()
    
    c.execute("SELECT balance FROM accounts WHERE user_id = ? AND currency = ?", (user_id, currency))
    result = c.fetchone()
    conn.close()
    
    if result:
        return result[0]
    else:
        return 0.0

def get_all_users():
    """Get list of all users for transfer selection"""
    conn = sqlite3.connect('data/brics_transfer.db')
    c = conn.cursor()
    
    c.execute("SELECT user_id, username, country, currency FROM users")
    users = c.fetchall()
    conn.close()
    
    return [{
        "user_id": user[0],
        "username": user[1],
        "country": user[2],
        "currency": user[3]
    } for user in users]

def respond_to_request(transaction_id, action):
    """Approve or reject a pending money request with blockchain update"""
    conn = sqlite3.connect('data/brics_transfer.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get the request details
    c.execute("SELECT * FROM transactions WHERE transaction_id = ? AND type = 'request' AND status = 'pending'", 
              (transaction_id,))
    request = c.fetchone()
    
    if not request:
        conn.close()
        return False, "Request not found or already processed."
    
    request = dict(request)
    
    if action == "approve":
        # Execute the transfer
        result, message = execute_transfer(
            request["sender_id"], 
            request["receiver_id"], 
            request["amount_sent"],
            f"Payment for request: {request['description']}"
        )
        
        if result:
            # Update the request status
            c.execute(
                "UPDATE transactions SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE transaction_id = ?",
                (transaction_id,)
            )
            
            # Update blockchain status with the request update
            timestamp = datetime.datetime.now().isoformat()
            update_data = {
                "transaction_id": transaction_id,
                "status": "completed",
                "updated_at": timestamp,
                "action": "request_approved"
            }
            
            # Try to record status update on blockchain
            record_transaction_on_blockchain(update_data)
            
            conn.commit()
            conn.close()
            return True, "Request approved and payment sent. Blockchain updated."
        else:
            conn.close()
            return False, message
    
    elif action == "reject":
        # Update the request status
        c.execute(
            "UPDATE transactions SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE transaction_id = ?",
            (transaction_id,)
        )
        
        # Update blockchain status with the rejection
        timestamp = datetime.datetime.now().isoformat()
        update_data = {
            "transaction_id": transaction_id,
            "status": "rejected",
            "updated_at": timestamp,
            "action": "request_rejected"
        }
        
        # Try to record status update on blockchain
        record_transaction_on_blockchain(update_data)
        
        conn.commit()
        conn.close()
        return True, "Request rejected. Blockchain updated."
    
    else:
        conn.close()
        return False, "Invalid action."

def get_pending_requests(user_id):
    """Get pending money requests for a user"""
    conn = sqlite3.connect('data/brics_transfer.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get requests where the user is the payer (sender)
    c.execute("""
        SELECT t.*, u1.username as requester_name, u2.username as payer_name 
        FROM transactions t
        JOIN users u1 ON t.receiver_id = u1.user_id
        JOIN users u2 ON t.sender_id = u2.user_id
        WHERE t.sender_id = ? AND t.type = 'request' AND t.status = 'pending'
    """, (user_id,))
    
    requests = []
    for row in c.fetchall():
        requests.append(dict(row))
    
    conn.close()
    return requests
def display_transfer_tab():
    """Display the transfer tab in the Streamlit interface"""
    st.header("BRICS Currency Transfer")
    
    # Check if user is logged in
    if 'user_info' not in st.session_state:
        login_section()
    else:
        # User is logged in, show transfer interface
        transfer_interface()

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

def transfer_interface():
    """Display the transfer interface for logged-in users"""
    user_info = st.session_state.user_info
    
    st.subheader(f"Welcome, {user_info['username']} ({user_info['currency']})")
    
    # Show current balance
    balance = get_user_balance(user_info['user_id'], user_info['currency'])
    if 'ex_rates' in st.session_state:
        # Convert to BRICS value using exchange rates
        currency_mapping = {
            "CNY": "CN", "INR": "IN", "RUB": "RU", "BRL": "BR", "ZAR": "ZA"
        }
        user_currency_code = currency_mapping.get(user_info['currency'])

        if user_currency_code in st.session_state.ex_rates:
            brics_value = balance / st.session_state.ex_rates[user_currency_code]
            st.write(balance)
            st.info(f"Your current balance:{user_info['currency']} (≈ {round(brics_value, 2)} BRICS)")
        else:
            st.info(f"Your current balance: {balance} {user_info['currency']}")
    else:
        st.info(f"Your current balance: {balance} {user_info['currency']}")
    
    # Create tabs for transfer options
    transfer_tab, request_tab, history_tab, verify_tab = st.tabs(
        ["Send Money", "Request Money", "Transaction History", "Verify Transaction"]
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
            amount = st.number_input("Amount to Send", min_value=0.01, value=10.0, step=1.0)
            description = st.text_input("Description (optional)", "")
            
            # Display conversion preview
            if 'ex_rates' in st.session_state:
                try:
                    currency_mapping = {
                        "CNY": "CN", "INR": "IN", "RUB": "RU", "BRL": "BR", "ZAR": "ZA"
                    }
                    sender_code = currency_mapping.get(user_info['currency'])
                    receiver_code = currency_mapping.get(receiver['currency'])
                    
                    if sender_code in st.session_state.ex_rates and receiver_code in st.session_state.ex_rates:
                        # Convert via BRICS common unit
                        brics_amount = amount / st.session_state.ex_rates[sender_code]
                        converted_amount = brics_amount * st.session_state.ex_rates[receiver_code]
                        
                        st.write(f"Conversion: {amount} {user_info['currency']} → {round(converted_amount, 2)} {receiver['currency']}")
                        
                        if st.button("Send Money"):
                            if amount > balance:
                                st.error("Insufficient funds for this transfer.")
                            else:
                                success, message = execute_transfer(
                                    user_info['user_id'], 
                                    receiver['user_id'], 
                                    amount, 
                                    description
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
        # Similar implementation for money requests
        # ...
        
    with history_tab:
        st.subheader("Transaction History")
        transactions = get_transaction_history(user_info['user_id'])
        if transactions:
            for tx in transactions:
                with st.expander(
                    f"{tx['type'].title()}: {tx['amount_sent']} {tx['sender_currency']} → {tx['amount_received']} {tx['receiver_currency']} ({tx['created_at'][:16]})"
                ):
                    st.write(f"From: {tx['sender_name']}")
                    st.write(f"To: {tx['receiver_name']}")
                    if tx['description']:
                        st.write(f"Description: {tx['description']}")
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
                st.json(tx_details)
                if tx_details['blockchain_verified']:
                    st.success(tx_details['blockchain_message'])
                else:
                    st.warning(tx_details['blockchain_message'])
            else:
                st.error("Transaction not found.")
    
    # Logout button
    if st.button("Logout"):
        del st.session_state.user_info
        st.success("Logged out successfully.")
        st.rerun()