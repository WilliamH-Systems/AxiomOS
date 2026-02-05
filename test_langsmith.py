import asyncio
from src.agent import AxiomOSAgent
from src.models import AgentRequestModel

def run_test():
    print("Starting LangSmith integration test...")
    agent = AxiomOSAgent()
    request = AgentRequestModel(message="Hello, world!", allow_web_search=False)

    print(f"Sending request to agent: {request.message}")
    response = agent.run(request)

    print(f"Agent response: {response.response}")
    print("LangSmith integration test finished.")
    print("Please check your LangSmith project for traces.")

if __name__ == "__main__":
    run_test()
