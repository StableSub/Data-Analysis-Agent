import os
from typing import Literal, Optional, TypedDict
from dotenv import load_dotenv, find_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv(find_dotenv())

class LLMSettings(TypedDict):
    """LLM 구성 정보를 담는 사전 구조."""
    model: str
    temperature: float
    api_key_env: str


LLM_PRESETS: dict[str, LLMSettings] = {
    "gemini_flash": {
        "model": "gemini-2.5-flash",
        "temperature": 0.4,
        "api_key_env": "GEMINI_FLASH_API_KEY",
    },
    "gemini_pro": {
        "model": "gemini-2.5-pro",
        "temperature": 0.2,
        "api_key_env": "GEMINI_PRO_API_KEY",
    },
}

LLMPresetName = Literal["gemini_flash", "gemini_pro"]


def _build_llm(model: str, temperature: float, api_key_env: str) -> ChatGoogleGenerativeAI:
    """필요한 환경변수를 검사해 ChatGoogleGenerativeAI 인스턴스를 생성한다."""
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"{model}을(를) 초기화하려면 환경변수 '{api_key_env}'가 필요합니다.")
    return ChatGoogleGenerativeAI(model=model, temperature=temperature, api_key=api_key)

def get_llm(preset: Optional[LLMPresetName] = None) -> ChatGoogleGenerativeAI:
    """
    프리셋 인자 혹은 LLM_PRESET 환경변수에 따라 LLM을 생성한다.

    동일한 프리셋 요청 시 중복 생성을 막기 위해 결과를 캐싱한다.
    """
    preset_name = preset
    settings = LLM_PRESETS.get(preset_name)
    if not settings:
        available = ", ".join(sorted(LLM_PRESETS))
        raise ValueError(f"알 수 없는 LLM 프리셋 '{preset_name}'. 사용 가능: {available}")
    return _build_llm(**settings)