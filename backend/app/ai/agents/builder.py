from aiohttp.web_middlewares import middleware
from typing import List

from langchain_core.tools import BaseTool
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call
from langchain.chat_models import init_chat_model
from langgraph.config import get_config
from langgraph.checkpoint.memory import InMemorySaver

from dotenv import load_dotenv

load_dotenv()

class AgentBuilder:
    """
        LangChain(LangGraph) 에이전트를 유연하게 생성하기 위한 빌더 클래스
    """
    def __init__(self, model_name: str = "gpt-5-nano"):
        self.model = model_name
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
            middleware=[self.dynamic_model_seletor],
            checkpointer=self.checkpointer,
        )
        return agent

    @staticmethod
    @wrap_model_call
    def dynamic_model_seletor(request, handler):
        config = get_config()
        model_id = config["configurable"].get("model_id")
        print(f"현재 모델은 {model_id}")
        if model_id is not request.model:
            new_model = init_chat_model(model_id)
            new_request = request.override(model=new_model)
            return handler(new_request)
        return None
