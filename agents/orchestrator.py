# agents/orchestrator.py

from agents.general_agent import GeneralAgent
from agents.insight_agent import InsightAgent
from agents.intent_router_agent import IntentRouterAgent
from agents.metadata_agent import MetadataAgent
from agents.metadata_insight_agent import MetadataInsightAgent
from agents.sql_agent import SQLAgent
from database.query_executor import QueryExecutor
from memory.chat_memory import ChatMemory
from memory.query_cache import QueryCache

from cache.redis_service import RedisService
from utils.cache_utils import generate_cache_key
from cache.semantic_cache import SemanticCache

import pandas as pd
import traceback
from datetime import datetime


class AnalyticsOrchestrator:

    def __init__(self):

        self.intent_router = IntentRouterAgent()
        self.general_agent = GeneralAgent()
        self.metadata_agent = MetadataAgent()
        self.metadata_insight_agent = MetadataInsightAgent()
        self.sql_agent = SQLAgent()
        self.query_executor = QueryExecutor()      
        self.insight_agent = InsightAgent()
        self.chat_memory = ChatMemory()
        self.query_cache = QueryCache()
        self.redis = RedisService()
        self.semantic_cache = SemanticCache()
  
    def generate_insight(
        self,
        question,
        sql,
        result,
        metadata,
        history
    ):
        
        print("=" * 80)
        print("GENERATE INSIGHT CALLED")
        print("=" * 80)

        insight = self.insight_agent.generate_insight(
            question=question,
            metadata=metadata,
            sql=sql,
            result=pd.DataFrame(result),
            history=history
        )
        
        self.chat_memory.add(
        question=question,
        sql=sql,
        result=result[:20],
        insight=insight
        )
        
        return insight
    
    def analyze_question(
        self,question: str):

        if question is None:
            return {
                "success": False,
                "error":
                "Question cannot be empty."
            }

        question = question.strip()

        if not question:
            return {
                "success": False,
                "error":
                "Please enter a question."
            }
    
        try:
            
            # ----------------------------
            # Redis Cache Check
            # ----------------------------
            cache_key = generate_cache_key(question)

            cached_response = self.redis.get(cache_key)

            if cached_response:
                print("✅ REDIS CACHE HIT")

                if cached_response.get("sql"):
                    self.chat_memory.add(
                        question=question,
                        sql=cached_response.get("sql"),
                        result=cached_response.get("result", []),
                        insight=cached_response.get("insight"),
                    )

                cached_response["cache_hit"] = True
                return cached_response

            print("❌ REDIS CACHE MISS")

            semantic_response = self.semantic_cache.search(question)

            if semantic_response:
                print("✅ SEMANTIC CACHE HIT")

                semantic_response["semantic_cache_hit"] = True

                if semantic_response.get("sql"):
                    self.chat_memory.add(
                        question=question,
                        sql=semantic_response.get("sql"),
                        result=semantic_response.get("result", []),
                        insight=semantic_response.get("insight"),
                    )

                return semantic_response
            
            print(f"❌ CACHE MISS: {cache_key}")
            
            # ==================================================
            # DETECT INTENT
            # ==================================================

            intent_result = (
                self.intent_router.classify(question))

            print("\n" + "=" * 80)
            print("INTENT ROUTER")
            print("=" * 80)
            print(intent_result)
            print("=" * 80)

            intent = intent_result.get(
                "intent",
                "sql_query"
            )

            print("\n" + "=" * 80)
            print("DETECTED INTENT")
            print("=" * 80)
            print(intent)
            print("=" * 80)

            # ==================================================
            # VALIDATE INTENT
            # ==================================================

            valid_intents = [
                "general",
                "metadata",
                "sql_query"
            ]

            if intent not in valid_intents:

                return {
                    "success": False,
                    "question": question,
                    "error":
                    f"Unsupported intent: {intent}"
                }

            # ==================================================
            # GENERAL
            # ==================================================

            if intent == "general":

                response = (
                    self.general_agent.respond(
                        question
                    )
                )

                response = {
                    "success": True,
                    "intent": "general",
                    "question": question,
                    "metadata": None,
                    "sql": "",
                    "result": None,
                    "insight": {
                        "answer": response.get(
                            "answer",
                            "No response generated."
                        )
                    }
                }
                
                response["cached_at"] = (datetime.now().isoformat())
                self.redis.set(cache_key, response, ttl=3600)
                print("✅ RESPONSE SAVED TO CACHE")
                self.semantic_cache.store_response(question,response)
                
                return response

            # ==================================================
            # RETRIEVE METADATA
            # ==================================================

            metadata_result = (
                self.metadata_agent.retrieve(
                    question
                )
            )

            if not metadata_result:

                return {
                    "success": False,
                    "intent": intent,
                    "question": question,
                    "error":
                    "Metadata retrieval failed."
                }

            # metadata_context = (
            #     metadata_result.get(
            #         "context",
            #         ""
            #     )
            # )

            # ==================================================
            # METADATA
            # ==================================================

            if intent == "metadata":

                insight = (
                    self.metadata_insight_agent
                    .generate_insight(
                        question=question,
                        metadata=metadata_result
                    )
                )

                response = {
                    "success": True,
                    "intent": "metadata",
                    "question": question,
                    "metadata": metadata_result,
                    "sql": "",
                    "result": None,
                    "insight": insight
                }

                response["insight"] = insight
                
                self.redis.set(cache_key, response, ttl=3600)
                print("✅ RESPONSE SAVED TO CACHE")
                self.semantic_cache.store_response(question,response)
                return response

            # ==================================================
            # SQL_QUERY
            # ==================================================

            if intent == "sql_query":

                sql_response = (
                    self.sql_agent.generate_sql(
                        question=question,
                        metadata=metadata_result
                    )
                )

                print("\n" + "=" * 80)
                print("SQL RESPONSE")
                print("=" * 80)
                print(sql_response)
                print("=" * 80)

                if not sql_response.get(
                    "success",
                    False
                ):

                    return {
                        "success": False,
                        "intent": "sql_query",
                        "question": question,
                        "metadata": metadata_result,
                        "error": sql_response.get(
                            "error",
                            "SQL generation failed."
                        )
                    }

                sql_query = (sql_response.get("sql", "").strip())

                if not sql_query:

                    return {
                        "success": False,
                        "intent": "sql_query",
                        "question": question,
                        "error":
                        "Generated SQL is empty."
                    }

                # ==================================================
                # SQL SAFETY VALIDATION
                # ==================================================

                dangerous_keywords = [
                    "drop ",
                    "delete ",
                    "truncate ",
                    "alter ",
                    "update ",
                    "grant ",
                    "revoke "
                ]

                if any(
                    keyword in sql_query.lower()
                    for keyword in dangerous_keywords
                ):

                    return {
                        "success": False,
                        "intent": "sql_query",
                        "question": question,
                        "sql": sql_query,
                        "error":
                        "Unsafe SQL detected."
                    }

                # ==================================================
                # EXECUTE QUERY
                # ==================================================

                print("\n" + "=" * 80)
                print("EXECUTING SQL")
                print("=" * 80)
                print(sql_query)
                print("=" * 80)

                result_df = (
                    self.query_executor.execute(
                        sql_query
                    )
                )
                
                self.chat_memory.add(
                    question=question,
                    sql=sql_query,
                    result=result_df.head(20).to_dict(
                    orient="records"),
                    insight=None
                    )

                print("\n" + "=" * 80)
                print("QUERY RESULT")
                print("=" * 80)

                if result_df is not None:
                    print(result_df.head())
                else:
                    print("NO RESULTS")

                print("=" * 80)

                response = {
                    "success": True,
                    "intent": "sql_query",
                    "question": question,
                    "sql": sql_query,
                    "result": result_df.to_dict(
                        orient="records"
                    ),
                    "row_count": (
                        len(result_df)
                        if result_df is not None
                        else 0 ),
                    "insight": None,
                    "insight_available": True
                }
                
                self.redis.set(cache_key, response, ttl=3600)
                self.semantic_cache.store_response(question,response)
                print("✅ RESPONSE SAVED TO CACHE")
                return response

            # ==================================================
            # FALLBACK
            # ==================================================

            return {
                "success": False,
                "question": question,
                "error": f"Unhandled intent: {intent}"
            }
            

        except Exception as ex:

            print("\n" + "=" * 80)
            print("ORCHESTRATOR ERROR")
            print("=" * 80)
            print(str(ex))
            print("=" * 80)

            traceback.print_exc()

            return {
                "success": False,
                "question": question,
                "error": str(ex)
            }