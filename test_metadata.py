# test_metadata.py

from agents.metadata_agent import MetadataAgent

agent = MetadataAgent()

result = agent.retrieve(
    "What is the average overall_total_score__c?"
)

print(result["context"])