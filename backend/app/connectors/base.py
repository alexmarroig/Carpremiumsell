from abc import ABC, abstractmethod
from typing import Iterable, Mapping


class BaseConnector(ABC):
    name: str

    @abstractmethod
    def fetch_listings(self) -> Iterable[Mapping]:  # pragma: no cover - interface
        """Fetch raw listing payloads respecting robots and ToS."""

    @abstractmethod
    def parse_listing(self, payload: Mapping) -> Mapping:  # pragma: no cover - interface
        """Parse HTML/JSON into structured data fields."""

    @abstractmethod
    def normalize_fields(self, parsed: Mapping) -> Mapping:  # pragma: no cover - interface
        """Map source fields into normalized schema."""
