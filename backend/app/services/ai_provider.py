from abc import ABC, abstractmethod
from typing import Dict


class AIProvider(ABC):
    @abstractmethod
    def chat(self, messages: list[Dict[str, str]]) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class MockProvider(AIProvider):
    def chat(self, messages: list[Dict[str, str]]) -> str:
        last_user = next((m for m in reversed(messages) if m["role"] == "user"), {"content": ""})
        return f"Entendido. Buscarei a melhor opção para: {last_user.get('content', '')}"
