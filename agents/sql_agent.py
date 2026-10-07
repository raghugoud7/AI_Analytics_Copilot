# agents/sql_agent.py

import json
import re

from llm.llm_factory import get_llm
from prompts.sql_prompt import SQL_AGENT_PROMPT
from cache.redis_service import RedisService

class SQLAgent:

    def __init__(self):
        self.llm = get_llm()
        self.redis = RedisService()

    def _clean_json(self, content: str) -> str:
        if not content:
            return ""

        content = (
            content.replace("```json", "")
            .replace("```", "")
            .strip()
        )

        match = re.search(
            r'<strong class="___1qwroh2 fl43uef f19n0e5" data-lexical-text="true">\{</strong>.*<strong class="___1qwroh2 fl43uef f19n0e5" data-lexical-text="true">\}</strong>',
            content,
            re.DOTALL,
        )

        if match:
            return match.group(0)

        return content

    def generate_sql(self, question: str, metadata: dict):
        try:
            cache_key = f"sql:{question.strip().lower()}"
            cached_sql = self.redis.get(cache_key)

            if cached_sql:
                print("✅ SQL CACHE HIT")
                return cached_sql

            print("\n" + "=" * 80)
            print("METADATA TYPE")
            print("=" * 80)
            print(type(metadata))
            print("=" * 80)

            metadata_context = metadata.get("context", "")

            prompt = SQL_AGENT_PROMPT.format(
                metadata=metadata_context,
                question=question,
            )

            response = self.llm.invoke(prompt)

            print("\n" + "=" * 80)
            print("RAW SQL AGENT RESPONSE")
            print("=" * 80)
            print(response.content)
            print("=" * 80)

            content = self._clean_json(response.content)

            print("\n" + "=" * 80)
            print("JSON TO PARSE")
            print("=" * 80)
            print(content)
            print("=" * 80)

            result = json.loads(content)

            if result.get("success") is False:
                return {
                    "success": False,
                    "error": result.get("error", "SQL generation failed."),
                }

            sql = (
                result.get("sql", "")
                .replace("```sql", "")
                .replace("```", "")
                .strip()
            )

            if not sql:
                return {
                    "success": False,
                    "error": "Empty SQL returned by model.",
                    "raw_response": content,
                }

            response = {
                "success": True,
                "business_intent": result.get("business_intent", "Unknown"),
                "analysis_type": result.get("analysis_type", "sql_query"),
                "required_tables": result.get("required_tables", []),
                "required_dimensions": result.get("required_dimensions", []),
                "required_measures": result.get("required_measures", []),
                "required_kpis": result.get("required_kpis", []),
                "recommended_chart": result.get("recommended_chart", ""),
                "sql": sql,
            }
            
            self.redis.set(cache_key, response, ttl=7200)  # Cache for 2 hours
            return response

        except json.JSONDecodeError as ex:
            print("\n" + "=" * 80)
            print("SQL JSON PARSE ERROR")
            print("=" * 80)
            print(str(ex))
            print("=" * 80)

            return {
                "success": False,
                "error": f"Unable to parse SQL Agent response: {str(ex)}",
            }

        except Exception as ex:
            print("\n" + "=" * 80)
            print("SQL AGENT ERROR")
            print("=" * 80)
            print(str(ex))
            print("=" * 80)

            return {"success": False, "error": str(ex)}