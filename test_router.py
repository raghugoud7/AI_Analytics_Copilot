# test_router.py

from agents.intent_router_agent import IntentRouterAgent


def run_tests():

    router = IntentRouterAgent()

    test_questions = [

        # General
        "who are you",
        "what can you do",
        "how can you help me",
        "thank you",
        "bye",
        "good morning",
        "good afternoon",
        "good evening",

        # Conversation
        "thanks",
        "okay",
        "goodbye",

        # Help
        "help",
        "examples",
        "sample questions",

        # Metadata
        "explain this dataset",
        "show available columns",
        "show available measures",
        "show available dimensions",
        "what tables are available",
        "describe schema",
        "what dashboard can be created"

        # SQL Queries
        "top 10 agents by quality score",
        "which region has the lowest score",
        "top 5 regions by quality score",
        "show score trend by month"

        "average quality score by region"

        "compare quality score between APAC and EMEA"

        "top 10 agents"

        "show poor performance agents"
    ]

    print("\n" + "=" * 100)
    print("INTENT ROUTER TEST")
    print("=" * 100)

    for question in test_questions:

        result = router.classify(question)

        print("\nQuestion:")
        print(question)

        print("Result:")
        print(result)

        print("-" * 100)


if __name__ == "__main__":
    run_tests()