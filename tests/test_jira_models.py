"""Tests for Jira Pydantic models."""

import json
from pathlib import Path
from dacrew.model import JiraWebhook


def load_sample_webhook() -> dict:
    """Load the sample webhook data from test resources."""
    webhook_file = Path(__file__).parent / "resources" / "sample_webhook_issue_updated.json"
    
    # Skip the header lines and extract just the JSON payload
    with open(webhook_file, 'r') as f:
        lines = f.readlines()
    
    # Find the JSON payload section
    json_start = None
    for i, line in enumerate(lines):
        if line.strip() == "Webhook payload:":
            json_start = i + 1
            break
    
    if json_start is None:
        raise ValueError("Could not find JSON payload in webhook file")
    
    # Extract and parse the JSON
    json_content = ''.join(lines[json_start:])
    return json.loads(json_content)


def test_webhook_model_validation():
    """Test that the webhook model can validate the sample data."""
    sample_data = load_sample_webhook()
    
    # This should not raise any exceptions
    webhook = JiraWebhook.model_validate(sample_data)
    
    # Verify key fields are correctly parsed
    assert webhook.webhookEvent == "jira:issue_updated"
    assert webhook.timestamp == 1756389284246
    assert webhook.issue is not None
    assert webhook.issue.key == "BTS-16"
    assert webhook.issue.fields.summary == "Upgrade hibernate-related dependencies"
    assert webhook.issue.fields.status.name == "Draft Requirement"
    assert webhook.issue.fields.priority.name == "Medium"
    assert webhook.issue.fields.issuetype.name == "Feature"
    assert webhook.issue.fields.project.key == "BTS"


def test_webhook_model_serialization():
    """Test that the webhook model can be serialized back to JSON."""
    sample_data = load_sample_webhook()
    webhook = JiraWebhook.model_validate(sample_data)
    
    # Convert back to dict
    webhook_dict = webhook.model_dump()
    
    # Verify key fields are preserved
    assert webhook_dict["webhookEvent"] == "jira:issue_updated"
    assert webhook_dict["timestamp"] == 1756389284246
    assert webhook_dict["issue"]["key"] == "BTS-16"
    assert webhook_dict["issue"]["fields"]["summary"] == "Upgrade hibernate-related dependencies"


def test_webhook_model_extra_fields():
    """Test that the model ignores extra fields as configured."""
    sample_data = load_sample_webhook()
    
    # Add some extra fields that shouldn't be in the model
    sample_data["extra_field"] = "extra_value"
    sample_data["issue"]["fields"]["custom_field"] = "custom_value"
    
    # This should still work without errors
    webhook = JiraWebhook.model_validate(sample_data)
    
    # The extra fields should be ignored
    assert not hasattr(webhook, "extra_field")
    assert webhook.issue.fields.summary == "Upgrade hibernate-related dependencies"


def test_webhook_model_missing_optional_fields():
    """Test that the model handles missing optional fields gracefully."""
    sample_data = load_sample_webhook()
    
    # Remove some optional fields
    del sample_data["user"]
    del sample_data["changelog"]
    
    # This should still work
    webhook = JiraWebhook.model_validate(sample_data)
    
    # Optional fields should be None
    assert webhook.user is None
    assert webhook.changelog is None
    assert webhook.issue is not None  # Required field should still be present


if __name__ == "__main__":
    # Run the tests
    test_webhook_model_validation()
    test_webhook_model_serialization()
    test_webhook_model_extra_fields()
    test_webhook_model_missing_optional_fields()
    print("All tests passed!")
