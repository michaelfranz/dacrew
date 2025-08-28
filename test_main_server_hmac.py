#!/usr/bin/env python3
"""
Test script to verify HMAC validation with the main server using actual Jira webhook format.
"""

import hmac
import hashlib
import json
import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def compute_hmac_sha256(data: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for the given data and secret."""
    return hmac.new(
        secret.encode('utf-8'),
        data,
        hashlib.sha256
    ).hexdigest()

def main():
    # Get secret from environment
    secret = os.getenv("JIRA_WEBHOOK_SECRET")
    if not secret:
        print("Error: JIRA_WEBHOOK_SECRET not found in environment variables")
        return
    
    print(f"Secret: {secret}")
    
    # Sample Jira webhook payload based on actual captured data
    webhook_payload = {
        "timestamp": 1756309738659,
        "webhookEvent": "jira:issue_updated",
        "issue_event_type_name": "issue_generic",
        "user": {
            "accountId": "712020:45fbc2bd-4957-4173-b56b-384ca65db155",
            "displayName": "Mike Mannion"
        },
        "issue": {
            "id": "10099",
            "key": "BTS-16",
            "fields": {
                "issuetype": {
                    "name": "Feature"
                },
                "project": {
                    "key": "BTS",
                    "name": "Karakun Agent Experimentation"
                },
                "summary": "Upgrade hibernate-related dependencies",
                "description": "The project, which is a multi-module Java project..."
            }
        }
    }
    
    # Convert to JSON bytes
    json_data = json.dumps(webhook_payload).encode('utf-8')
    
    # Compute HMAC
    signature = compute_hmac_sha256(json_data, secret)
    full_signature = f"sha256={signature}"
    
    print(f"Webhook payload: {json.dumps(webhook_payload, indent=2)}")
    print(f"JSON data length: {len(json_data)} bytes")
    print(f"Computed signature: {signature}")
    print(f"Full signature header: {full_signature}")
    
    # Test with main server (assuming it's running on localhost:8000)
    try:
        response = requests.post(
            "http://localhost:8000/webhook/jira",
            headers={
                "X-Hub-Signature": full_signature,
                "Content-Type": "application/json"
            },
            data=json_data,
            timeout=10
        )
        
        print(f"\nResponse status: {response.status_code}")
        print(f"Response body: {response.text}")
        
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to server. Make sure the main server is running on localhost:8000")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    main()
