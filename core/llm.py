import os
from typing import Any
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_models import ChatOllama

_DEF_MODEL = os.getenv("OLLAMA_MODEL", "gemma:2b")  # set via .env if needed

def get_interviewer_lm() -> Any:
    return ChatOllama(model=_DEF_MODEL, temperature=0.2)

def get_evaluator_lm() -> Any:
    return ChatOllama(model=_DEF_MODEL, temperature=0.0)