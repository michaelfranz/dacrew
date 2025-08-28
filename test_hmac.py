#!/usr/bin/env python3
"""
Test script to verify HMAC signature generation and validation.
"""

import hmac
import hashlib
import json
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
    
    # Test data
    test_data = {
        "test": "data",
        "timestamp": "2024-01-01T12:00:00Z"
    }
    
    # Convert to JSON bytes
    json_data = json.dumps(test_data).encode('utf-8')
    
    # Compute HMAC
    signature = compute_hmac_sha256(json_data, secret)
    full_signature = f"sha256={signature}"
    
    print(f"Test data: {test_data}")
    print(f"JSON data: {json_data}")
    print(f"Computed signature: {signature}")
    print(f"Full signature header: {full_signature}")
    
    # Test verification
    def verify_hmac_signature(data: bytes, signature_header: str, secret: str) -> bool:
        """Verify HMAC signature from X-Hub-Signature header."""
        if not signature_header:
            return False
        
        # Extract the signature value (remove 'sha256=' prefix)
        if signature_header.startswith('sha256='):
            expected_signature = signature_header[7:]  # Remove 'sha256=' prefix
        else:
            expected_signature = signature_header
        
        # Compute the actual signature
        actual_signature = compute_hmac_sha256(data, secret)
        
        # Compare signatures (use hmac.compare_digest for timing attack protection)
        return hmac.compare_digest(expected_signature, actual_signature)
    
    # Test verification
    is_valid = verify_hmac_signature(json_data, full_signature, secret)
    print(f"Verification result: {is_valid}")
    
    # Test with wrong signature
    wrong_signature = "sha256=wrongsignature"
    is_valid_wrong = verify_hmac_signature(json_data, wrong_signature, secret)
    print(f"Verification with wrong signature: {is_valid_wrong}")

if __name__ == "__main__":
    main()
