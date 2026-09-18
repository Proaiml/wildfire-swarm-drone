"""
PyreSwarm - Dağıtık İletişim ve Olay Veriyolu (Event-Driven Message Bus)
Farklı düğümler (drones, GCS, backend, optimizer) arasındaki asenkron mesajlaşmayı yönetir.
InMemoryBus, WebSocket entegrasyonu ve MQTT topic formatını standartlaştırır.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Callable, Any, Optional, Tuple
import time
import json


@dataclass
class SwarmEvent:
    topic: str
    sender_id: str
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class MessageBus(ABC):
    """Mesaj veriyolu soyut arayüzü."""

    @abstractmethod
    def subscribe(self, topic_pattern: str, callback: Callable[[SwarmEvent], None]):
        pass

    @abstractmethod
    def publish(self, event: SwarmEvent):
        pass


class InMemoryBus(MessageBus):
    """
    Yerel simülasyon ve tek makine dağıtımları için hafif, sıfır gecikmeli bellek içi veriyolu.
    """

    def __init__(self):
        # topic -> List[callbacks]
        self._subscribers: Dict[str, List[Callable[[SwarmEvent], None]]] = {}
        self._wildcard_subscribers: List[Tuple[str, Callable[[SwarmEvent], None]]] = []
        self._event_log: List[SwarmEvent] = []

    def subscribe(self, topic_pattern: str, callback: Callable[[SwarmEvent], None]):
        if "#" in topic_pattern or "+" in topic_pattern:
            self._wildcard_subscribers.append((topic_pattern, callback))
        else:
            if topic_pattern not in self._subscribers:
                self._subscribers[topic_pattern] = []
            self._subscribers[topic_pattern].append(callback)

    def publish(self, event: SwarmEvent):
        self._event_log.append(event)
        # 1. Birebir eşleşen aboneler
        if event.topic in self._subscribers:
            for cb in self._subscribers[event.topic]:
                try:
                    cb(event)
                except Exception as e:
                    print(f"[InMemoryBus] Abone hatası ({event.topic}): {e}")

        # 2. Joker (wildcard) aboneler
        for pattern, cb in self._wildcard_subscribers:
            if self._matches_pattern(event.topic, pattern):
                try:
                    cb(event)
                except Exception as e:
                    print(f"[InMemoryBus] Joker abone hatası: {e}")

    def _matches_pattern(self, topic: str, pattern: str) -> bool:
        """MQTT tarzı '+' ve '#' joker eşleştirmesi."""
        if pattern == "#":
            return True
        t_parts = topic.split("/")
        p_parts = pattern.split("/")

        for i, p in enumerate(p_parts):
            if p == "#":
                return True
            if i >= len(t_parts):
                return False
            if p != "+" and p != t_parts[i]:
                return False

        return len(t_parts) == len(p_parts)

    def get_event_history(self, limit: int = 100) -> List[SwarmEvent]:
        return self._event_log[-limit:]
