"""Hardcoded test configuration for negotiation orchestration tests.

Provides realistic but deterministic persona, authority framework,
playbook, and instructions constants used across Phase 10 tests.
These replace LLM-generated configuration in test scenarios.
"""

TEST_PERSONA = {
    "role": "Commercial solicitor",
    "style": "Collaborative but firm",
    "speciality": "Supply agreements",
}

TEST_AUTHORITY = {
    "green_zone": [
        "Standard boilerplate changes",
        "Minor wording improvements",
        "Obvious accepts (e.g., fixing typos)",
    ],
    "amber_zone": [
        "Payment terms",
        "Liability caps",
        "Indemnity scope",
        "Warranty periods",
    ],
    "red_zone": [
        "Governing law changes",
        "Jurisdiction changes",
        "Regulatory compliance terms",
    ],
}

TEST_PLAYBOOK = {
    "payment_terms": {
        "position": "45 days",
        "fallback": "30 days",
        "walkaway": "Net 15",
    },
    "warranty_period": {
        "position": "18 months",
        "fallback": "12 months",
        "walkaway": "6 months",
    },
    "liability_cap": {
        "position": "Total contract value",
        "fallback": "2x annual fees",
        "walkaway": "No cap",
    },
}

TEST_INSTRUCTIONS = (
    "Push back on any liability caps below total contract value. "
    "Accept standard boilerplate changes. "
    "Counter-propose payment terms to 45 days. "
    "Accept confidentiality provisions as drafted."
)
