# test_general_agent.py

from agents.general_agent import (
    GeneralAgent
)


def main():

    agent = GeneralAgent()

    print(
        "\nGeneral Agent Test"
    )

    print(
        "Type 'exit' to quit.\n"
    )

    while True:

        question = input(
            "\nYou: "
        )

        if question.lower() == "exit":
            break

        response = (
            agent.respond(
                question
            )
        )

        print(
            "\nAssistant:",
            response.get(
                "answer",
                "No answer"
            )
        )


if __name__ == "__main__":

    main()