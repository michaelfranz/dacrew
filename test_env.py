#!/usr/bin/env python3
"""
Test environment variable loading.
"""

from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get secret from environment
secret = os.getenv("JIRA_WEBHOOK_SECRET")
print(f"JIRA_WEBHOOK_SECRET: {secret}")

if not secret:
    print("Error: JIRA_WEBHOOK_SECRET not found in environment variables")
else:
    print("Success: JIRA_WEBHOOK_SECRET loaded from .env file")
