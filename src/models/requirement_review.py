from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from enum import Enum

class ReviewResult(str, Enum):
    PASS = "✅"
    FAIL = "❌"

class ReviewDecision(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

class ReviewCheck(BaseModel):
    check_name: str
    result: ReviewResult
    reason: str = ""

class RequirementReview(BaseModel):
    synopsis: Optional[str] = None
    checks: List[ReviewCheck] = Field(default_factory=list)
    reformulated_requirement: Optional[str] = None
    final_decision: ReviewDecision = ReviewDecision.REJECTED
    original_requirement: str = ""
    ticket_key: str = ""

    @field_validator('checks')
    @classmethod
    def validate_checks(cls, v):
        if len(v) != 8:
            raise ValueError("Must have exactly 8 checks")
        return v

    def get_jira_status(self) -> str:
        """
        Get the appropriate JIRA status based on the review decision.

        Returns:
            JIRA status string
        """
        if self.final_decision == ReviewDecision.ACCEPTED:
            return "ACCEPTED"
        else:
            return "REJECTED"

    def to_adf_document(self) -> Dict[str, Any]:
        """
        Convert the review to Atlassian Document Format (ADF) for JIRA comments.

        Returns:
            ADF document dictionary
        """
        # Create the main document structure
        doc = {
            "version": 1,
            "type": "doc",
            "content": []
        }

        # Add synopsis if available
        if self.synopsis:
            doc["content"].append({
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Review Synopsis"}]
            })
            doc["content"].append({
                "type": "paragraph",
                "content": [{"type": "text", "text": self.synopsis}]
            })

        # Add review summary header
        doc["content"].append({
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Review Summary"}]
        })

        # Add decision with status
        decision_text = f"**Decision:** {self.final_decision.value}"
        if self.final_decision == ReviewDecision.ACCEPTED:
            decision_text += " ✅"
        else:
            decision_text += " ❌"

        doc["content"].append({
            "type": "paragraph",
            "content": [{"type": "text", "text": decision_text, "marks": [{"type": "strong"}]}]
        })

        # Add checks table
        doc["content"].append({
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"type": "text", "text": "Quality Checks"}]
        })

        # Create table for checks
        table_rows = []

        # Header row
        table_rows.append({
            "type": "tableRow",
            "content": [
                {
                    "type": "tableHeader",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Check", "marks": [{"type": "strong"}]}]}]
                },
                {
                    "type": "tableHeader",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Result", "marks": [{"type": "strong"}]}]}]
                },
                {
                    "type": "tableHeader",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Reason", "marks": [{"type": "strong"}]}]}]
                }
            ]
        })

        # Data rows
        for check in self.checks:
            table_rows.append({
                "type": "tableRow",
                "content": [
                    {
                        "type": "tableCell",
                        "content": [{"type": "paragraph", "content": [{"type": "text", "text": check.check_name}]}]
                    },
                    {
                        "type": "tableCell",
                        "content": [{"type": "paragraph", "content": [{"type": "text", "text": check.result.value}]}]
                    },
                    {
                        "type": "tableCell",
                        "content": [{"type": "paragraph", "content": [{"type": "text", "text": check.reason or ""}]}]
                    }
                ]
            })

        # Add table to document
        doc["content"].append({
            "type": "table",
            "content": table_rows
        })

        # Add reformulated requirement if available
        if self.reformulated_requirement:
            doc["content"].append({
                "type": "heading",
                "attrs": {"level": 3},
                "content": [{"type": "text", "text": "Reformulated Requirement"}]
            })
            doc["content"].append({
                "type": "codeBlock",
                "attrs": {"language": "text"},
                "content": [{"type": "text", "text": self.reformulated_requirement}]
            })

        # Add summary statistics
        passed_count = len([c for c in self.checks if c.result == ReviewResult.PASS])
        total_count = len(self.checks)

        doc["content"].append({
            "type": "paragraph",
            "content": [
                {"type": "text", "text": f"Quality Score: {passed_count}/{total_count} checks passed", "marks": [{"type": "strong"}]}
            ]
        })

        return doc