"""HMAC utilities for webhook signature validation."""

import hmac
import hashlib
import logging

logger = logging.getLogger(__name__)


def compute_hmac_sha256(data: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for given data and secret."""
    try:
        signature = hmac.new(
            secret.encode('utf-8'),
            data,
            hashlib.sha256
        ).hexdigest()
        return signature
    except Exception as e:
        logger.error(f"Error computing HMAC signature: {e}")
        raise


def verify_hmac_signature(data: bytes, signature_header: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature from webhook request."""
    try:
        # Extract signature from header (format: "sha256=<signature>")
        if not signature_header.startswith("sha256="):
            logger.error("Invalid signature header format")
            return False
        
        expected_signature = signature_header[7:]  # Remove "sha256=" prefix
        
        # Compute expected signature
        computed_signature = compute_hmac_sha256(data, secret)
        
        # Compare signatures (constant-time comparison)
        return hmac.compare_digest(computed_signature, expected_signature)
        
    except Exception as e:
        logger.error(f"Error verifying HMAC signature: {e}")
        return False
