from langchain.tools import tool
from langchain_tavily import TavilySearch


@tool
def search(query: str) -> str:
    wrapped = TavilySearch(max_results=5)
    results = wrapped.invoke({"query": query})
    return str(results)


TOOLS = [search]
