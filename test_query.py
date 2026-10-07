# test_query.py

from agents.metadata_agent import MetadataAgent
from agents.sql_agent import SQLAgent
from database.query_executor import QueryExecutor

question = (
    "Which regions have the lowest quality score?"
)

metadata = MetadataAgent().retrieve(
    question
)

sql_response = SQLAgent().generate_sql(
    question=question,
    metadata=metadata
)

print(sql_response)

sql = sql_response["sql"]

df = QueryExecutor().execute(sql)

print(df.head())