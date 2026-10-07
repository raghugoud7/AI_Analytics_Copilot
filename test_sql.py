# test_sql.py

from agents.metadata_agent import MetadataAgent
from agents.sql_agent import SQLAgent

question = (
    "Which regions have the lowest quality score?"
)

metadata = MetadataAgent().retrieve(
    question
)

sql = SQLAgent().generate_sql(
    question=question,
    metadata=metadata
)

print(sql)