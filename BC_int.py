import os
import json
import requests
import hashlib
import time

# Try to import Fabric SDK, fallback to REST API if not available
try:
    from fabric_sdk_py.client import Client
    from fabric_sdk_py.user import create_user
    FABRIC_SDK_AVAILABLE = True
except ImportError:
    FABRIC_SDK_AVAILABLE = False

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
        import streamlit as st
        st.error(f"Error initializing Fabric client: {str(e)}")
        # Fallback to local mode if Fabric is not available
        st.warning("Fabric blockchain unavailable. Falling back to local database only.")
        return None, None, "local"

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