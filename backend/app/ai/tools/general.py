from langchain_tavily import TavilySearch
from langchain.tools import tool

@tool
def search(query: str) -> str:
    """
    최신 정보를 검색을 통해 최대 5개의 결과를 반환합니다.
    """
    wrapped = TavilySearch(max_results=5)
    results = wrapped.invoke({"query": query})
    return str(results)

TOOLS = [search]