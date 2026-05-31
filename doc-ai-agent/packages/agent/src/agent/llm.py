from functools import lru_cache
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from config.settings import get_settings
from langchain_ollama import ChatOllama

settings = get_settings(service_name="agent")

USE_LOCAL = settings.use_local

@lru_cache(maxsize=4)
def get_llm(thinking: bool = False) -> ChatGoogleGenerativeAI:

    if USE_LOCAL:
        return ChatOllama(
            model="qwen3:14b",
            temp=0,
            num_ctx=16384,
        )

    return ChatGroq(
        model="qwen/qwen3-32b",
        api_key=settings.groq_api_key,
        temperature=0,
        reasoning_effort="none"
        )

    # return ChatGoogleGenerativeAI(
    #     model=settings.agent_model,
    #     google_api_key=settings.google_api_key,
    #     temperature=0 if not thinking else 1,
    #     model_kwargs={"thinking_budget": 1024 if thinking else 0},
    # )
