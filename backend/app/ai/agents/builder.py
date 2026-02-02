from typing import List

from langchain_core.tools import BaseTool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI

from dotenv import load_dotenv

load_dotenv()

class AgentBuilder:
    """
        LangChain(LangGraph) 에이전트를 유연하게 생성하기 위한 빌더 클래스
    """
    def __init__(self, model_name: str = "gpt-5-nano"):
        self.model = ChatOpenAI(model=model_name)
        self.tools: List[BaseTool] = []
        self.checkpointer = InMemorySaver()
        self.system_message: str = "You are a helpful AI assistant."

    def add_tool(self, tool: BaseTool) -> "AgentBuilder":
        self.tools.append(tool)
        return self

    def set_system_message(self, message: str) -> "AgentBuilder":
        self.system_message = message
        return self

    def build(self):
        agent = create_agent(
            model=self.model,
            tools=self.tools,
            checkpointer=self.checkpointer,
        )
        return agent
