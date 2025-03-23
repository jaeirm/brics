import sqlite3
import os
import uuid
import datetime
import json
import hashlib
import streamlit as st

# Create database directory if it doesn't exist
if not os.path.exists("data"):
    os.makedirs("data")

def init_notifications_table():
    """Initialize the notifications table"""
    conn = sqlite3.connect('data/brics_transfer.db')
    c = conn.cursor()
    
    # Create notifications table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
                notification_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL, 
                message TEXT NOT NULL,
                transaction_id TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
                )''')
    
    conn.commit()
    conn.close()

def init_db():
    """Setup the SQLite database"""
    conn = sqlite3.connect('data/brics_transfer.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
            notification_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL, 
            message TEXT NOT NULL,
            transaction_id TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
            )''')

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
    init_notification_preferences()
    init_notifications_table()
    conn.commit()
    conn.close()

def create_notification(user_id, title, message, transaction_id=None):
    """Create a new notification for a user"""
    conn = sqlite3.connect('data/brics_transfer.db')
    c = conn.cursor()
    
    notification_id = str(uuid.uuid4())
    
    try:
        c.execute(
            "INSERT INTO notifications (notification_id, user_id, title, message, transaction_id) VALUES (?, ?, ?, ?, ?)",
            (notification_id, user_id, title, message, transaction_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        return False

def get_user_notifications(user_id, include_read=False):
    """Get notifications for a user"""
    conn = sqlite3.connect('data/brics_transfer.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if include_read:
        c.execute(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
    else:
        c.execute(
            "SELECT * FROM notifications WHERE user_id = ? AND is_read = 0 ORDER BY created_at DESC",
            (user_id,)
        )
    
    notifications = [dict(row) for row in c.fetchall()]
    conn.close()
    return notifications

def mark_notification_as_read(notification_id):
    """Mark a notification as read"""
    conn = sqlite3.connect('data/brics_transfer.db')
    c = conn.cursor()
    
    try:
        c.execute(
            "UPDATE notifications SET is_read = 1 WHERE notification_id = ?",
            (notification_id,)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        return False

def get_unread_notification_count(user_id):
    """Get count of unread notifications for a user"""
    conn = sqlite3.connect('data/brics_transfer.db')
    c = conn.cursor()
    
    c.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
        (user_id,)
    )
    
    count = c.fetchone()[0]
    conn.close()
    return count

def init_notification_preferences():
    """Initialize notification preferences table"""
    conn = sqlite3.connect('data/brics_transfer.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS notification_preferences (
                user_id TEXT PRIMARY KEY,
                receive_payment_notify BOOLEAN DEFAULT 1,
                send_payment_notify BOOLEAN DEFAULT 1,
                request_notify BOOLEAN DEFAULT 1,
                request_response_notify BOOLEAN DEFAULT 1,
                push_enabled BOOLEAN DEFAULT 1,
                email_enabled BOOLEAN DEFAULT 0,
                email TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
                )''')
    
    conn.commit()
    conn.close()

def get_notification_preferences(user_id):
    """Get notification preferences for a user"""
    conn = sqlite3.connect('data/brics_transfer.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Check if preferences exist
    c.execute("SELECT * FROM notification_preferences WHERE user_id = ?", (user_id,))
    prefs = c.fetchone()
    
    if not prefs:
        # Create default preferences
        c.execute(
            "INSERT INTO notification_preferences (user_id) VALUES (?)",
            (user_id,)
        )
        conn.commit()
        
        # Fetch the new preferences
        c.execute("SELECT * FROM notification_preferences WHERE user_id = ?", (user_id,))
        prefs = c.fetchone()
    
    conn.close()
    return dict(prefs) if prefs else None

def update_notification_preferences(user_id, preferences):
    """Update notification preferences for a user"""
    conn = sqlite3.connect('data/brics_transfer.db')
    c = conn.cursor()
    
    try:
        # Update each preference that's provided
        valid_fields = [
            'receive_payment_notify', 'send_payment_notify', 'request_notify', 
            'request_response_notify', 'push_enabled', 'email_enabled', 'email'
        ]
        
        updates = []
        values = []
        
        for field, value in preferences.items():
            if field in valid_fields:
                updates.append(f"{field} = ?")
                values.append(value)
        
        if not updates:
            conn.close()
            return False, "No valid preferences to update."
        
        # Add user_id to values
        values.append(user_id)
        
        c.execute(
            f"UPDATE notification_preferences SET {', '.join(updates)} WHERE user_id = ?",
            tuple(values)
        )
        conn.commit()
        conn.close()
        return True, "Notification preferences updated successfully."
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, f"Error updating preferences: {str(e)}"

# User authentication functions
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

# Hash utilities
def generate_transaction_hash(transaction_data):
    """Generate a secure hash for the transaction data"""
    # Convert transaction data to string and encode
    tx_string = json.dumps(transaction_data, sort_keys=True)
    # Create SHA-256 hash
    return hashlib.sha256(tx_string.encode()).hexdigest()