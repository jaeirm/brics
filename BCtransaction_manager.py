import sqlite3
import datetime
import uuid
import json
import streamlit as st

from BCdatabase import get_user_balance, generate_transaction_hash, create_notification, get_notification_preferences
from BC_int import record_transaction_on_blockchain, verify_transaction_on_blockchain

def should_notify(user_id, notification_type):
    """Check if user should receive a notification of this type"""
    prefs = get_notification_preferences(user_id)
    if not prefs:
        return True  # Default is to notify
    
    # Check if notifications are enabled at all
    if prefs['push_enabled'] != 1:
        return False
    
    # Check specific notification type
    if notification_type == 'receive_payment':
        return prefs['receive_payment_notify'] == 1
    elif notification_type == 'send_payment':
        return prefs['send_payment_notify'] == 1
    elif notification_type == 'request':
        return prefs['request_notify'] == 1
    elif notification_type == 'request_response':
        return prefs['request_response_notify'] == 1
    
    return True


def execute_transfer(sender_id, receiver_id, amount, description="", is_brics_amount=False):
    """
    Execute a transfer between users with blockchain validation
    Can accept either local currency amount or BRICS amount
    """
    conn = sqlite3.connect('data/brics_transfer.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get sender's and receiver's currencies
    c.execute("SELECT currency FROM users WHERE user_id = ?", (sender_id,))
    sender_currency = c.fetchone()["currency"]
    
    c.execute("SELECT currency FROM users WHERE user_id = ?", (receiver_id,))
    receiver_currency = c.fetchone()["currency"]
    
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
    
    # Convert amount based on input type (local or BRICS)
    if is_brics_amount:
        # Convert from BRICS to sender's currency for the actual deduction
        brics_amount = amount  # Already in BRICS
        amount = brics_amount * st.session_state.ex_rates[sender_rate_key]  # Convert to sender's currency
    else:
        # Convert from sender's currency to BRICS
        brics_amount = amount / st.session_state.ex_rates[sender_rate_key]
    
    # Convert BRICS amount to receiver's currency
    converted_amount = brics_amount * st.session_state.ex_rates[receiver_rate_key]
    
    # Check if sender has sufficient balance
    sender_balance = get_user_balance(sender_id, sender_currency)
    if sender_balance < amount:
        conn.close()
        return False, "Insufficient balance for this transfer."
    
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
        "brics_amount": brics_amount,
        "exchange_rate_sender": st.session_state.ex_rates[sender_rate_key],
        "exchange_rate_receiver": st.session_state.ex_rates[receiver_rate_key],
        "timestamp": timestamp,
        "type": "transfer",
        "description": description
    }
    
    # Generate blockchain hash
    blockchain_hash = generate_transaction_hash(transaction_data)
    if should_notify(receiver_id, 'receive_payment'):
        c.execute("SELECT username FROM users WHERE user_id = ?", (sender_id,))
        sender_name = c.fetchone()["username"]
        
        notification_title = "Payment Received"
        notification_message = f"You received {round(converted_amount, 2)} {receiver_currency} ({round(brics_amount, 2)} BRICS) from {sender_name}."
        if description:
            notification_message += f" Message: '{description}'"
        
        create_notification(receiver_id, notification_title, notification_message, transaction_id)
    if should_notify(sender_id, 'send_payment'):
        c.execute("SELECT username FROM users WHERE user_id = ?", (receiver_id,))
        receiver_name = c.fetchone()["username"]
        
        sender_notification_title = "Payment Sent"
        sender_notification_message = f"You sent {round(amount, 2)} {sender_currency} ({round(brics_amount, 2)} BRICS) to {receiver_name}."
        
        create_notification(sender_id, sender_notification_title, sender_notification_message, transaction_id)
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
        
        # Return success with blockchain status information and BRICS value
        if bc_success:
            return True, f"Successfully transferred {round(amount, 2)} {sender_currency} ({round(brics_amount, 2)} BRICS) to {round(converted_amount, 2)} {receiver_currency}. Blockchain confirmation: successful."
            c.execute("SELECT username FROM users WHERE user_id = ?", (sender_id,))
            sender_name = c.fetchone()["username"]

            notification_title = "Payment Received"
            notification_message = f"You received {round(converted_amount, 2)} {receiver_currency} ({round(brics_amount, 2)} BRICS) from {sender_name}."
            if description:
                notification_message += f" Message: '{description}'"

            create_notification(receiver_id, notification_title, notification_message, transaction_id)

            # Also create notification for the sender
            c.execute("SELECT username FROM users WHERE user_id = ?", (receiver_id,))
            receiver_name = c.fetchone()["username"]

            sender_notification_title = "Payment Sent"
            sender_notification_message = f"You sent {round(amount, 2)} {sender_currency} ({round(brics_amount, 2)} BRICS) to {receiver_name}."

            create_notification(sender_id, sender_notification_title, sender_notification_message, transaction_id)

        else:
            return True, f"Transfer completed in local database. {round(amount, 2)} {sender_currency} ({round(brics_amount, 2)} BRICS) to {round(converted_amount, 2)} {receiver_currency}. Note: {bc_message}"
    
    except Exception as e:
        # Rollback in case of error
        conn.rollback()
        conn.close()
        return False, f"Error executing transfer: {str(e)}"
    

def request_money(requester_id, payer_id, amount, description="", is_brics_amount=False, is_requester_currency=False):
    """
    Create a money request with blockchain record and BRICS values
    Supports requests in BRICS, payer's currency, or requester's currency
    """
    conn = sqlite3.connect('data/brics_transfer.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get currencies
    c.execute("SELECT currency FROM users WHERE user_id = ?", (requester_id,))
    requester_currency = c.fetchone()["currency"]
    
    c.execute("SELECT currency FROM users WHERE user_id = ?", (payer_id,))
    payer_currency = c.fetchone()["currency"]
    
    # Map currency codes to exchange rate keys
    currency_mapping = {
        "CNY": "CN", "INR": "IN", "RUB": "RU", "BRL": "BR", "ZAR": "ZA"
    }
    
    # Check if exchange rates are available
    if "ex_rates" not in st.session_state:
        conn.close()
        return False, "Exchange rates not available. Please calculate values first."
    
    payer_rate_key = currency_mapping.get(payer_currency)
    requester_rate_key = currency_mapping.get(requester_currency)
    
    if payer_rate_key not in st.session_state.ex_rates or requester_rate_key not in st.session_state.ex_rates:
        conn.close()
        return False, f"Exchange rate missing for {payer_currency} or {requester_currency}."
    
    # Calculate the appropriate amounts based on input type
    if is_brics_amount:
        # Amount is already in BRICS
        brics_amount = amount
        # Convert BRICS to payer's currency for the request
        payer_amount = brics_amount * st.session_state.ex_rates[payer_rate_key]
        requester_amount = brics_amount * st.session_state.ex_rates[requester_rate_key]
    elif is_requester_currency:
        # Amount is in requester's currency
        requester_amount = amount
        # Convert to BRICS
        brics_amount = amount / st.session_state.ex_rates[requester_rate_key]
        # Convert to payer's currency
        payer_amount = brics_amount * st.session_state.ex_rates[payer_rate_key]
    else:
        # Amount is in payer's currency
        payer_amount = amount
        # Convert to BRICS
        brics_amount = amount / st.session_state.ex_rates[payer_rate_key]
        # Convert to requester's currency
        requester_amount = brics_amount * st.session_state.ex_rates[requester_rate_key]
    
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
        "amount": payer_amount,  # Store in payer's currency
        "amount_in_requester_currency": requester_amount,
        "brics_amount": brics_amount,
        "exchange_rate_payer": st.session_state.ex_rates[payer_rate_key],
        "exchange_rate_requester": st.session_state.ex_rates[requester_rate_key],
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
             payer_amount, requester_amount, "pending", "request", description, blockchain_hash, "pending")
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
        
        c.execute("SELECT username FROM users WHERE user_id = ?", (requester_id,))
        requester_name = c.fetchone()["username"]

        notification_title = "Money Request"
        notification_message = f"{requester_name} requested {round(payer_amount, 2)} {payer_currency} ({round(brics_amount, 2)} BRICS) from you."
        if description:
            notification_message += f" Reason: '{description}'"

        create_notification(payer_id, notification_title, notification_message, transaction_id)
        # Return success with blockchain status information and all value representations
        brics_info = f" ({round(brics_amount, 2)} BRICS)"
        requester_info = f", equivalent to {round(requester_amount, 2)} {requester_currency}"
        
        if bc_success:
            return True, f"Money request for {round(payer_amount, 2)} {payer_currency}{brics_info}{requester_info} sent successfully. Request ID: {transaction_id}. Blockchain confirmation: successful."
        else:
            return True, f"Money request for {round(payer_amount, 2)} {payer_currency}{brics_info}{requester_info} sent successfully. Request ID: {transaction_id}. Note: {bc_message}"
        conn.close()
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, f"Error creating request: {str(e)}"

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
            c.execute("SELECT username FROM users WHERE user_id = ?", (request["sender_id"],))
            payer_name = c.fetchone()["username"]

            notification_title = "Request Approved"
            notification_message = f"{payer_name} approved your request for {round(request['amount_received'], 2)} {request['receiver_currency']}."

            create_notification(request["receiver_id"], notification_title, notification_message, transaction_id)
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