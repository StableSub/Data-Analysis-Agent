from langchain_core.tools import tool

@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the internal knowledge base for information about manufacturing data analysis.
    Use this tool when user asks about domain-specific knowledge.
    """
    return f"검색 결과: '{query}'에 대한 관련 문서를 찾았습니다. 내용은 다음과 같습니다..."

@tool
def calculate_statistics(data_desc: str) -> str:
    """
    Calculate basic statistics for the given data description.
    """
    return f"통계 결과: {data_desc}의 평균은 50, 표준편차는 10입니다."
