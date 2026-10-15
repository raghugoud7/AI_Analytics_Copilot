# config/privacy.py

# Administrator-defined exclusions. Users cannot deselect these.
MANDATORY_COLUMNS = frozenset(
    {
        "phone_number__c",
        "person_account__c",
    }
)

# Backward compatibility with existing imports.
SENSITIVE_COLUMNS = MANDATORY_COLUMNS

# Optional suggestions from configuration.
# Dynamic REVIEW results will also be suggested.
SECONDARY_PII_COLUMNS = frozenset()

# Optional administrator-managed rules for individual tables.
TABLE_PRIVACY_RULES = {
    # "salesforce.lead": {
    #     "mandatory": {"reviewed_contact_column"},
    #     "suggested": {"reviewed_secondary_column"},
    # },
}