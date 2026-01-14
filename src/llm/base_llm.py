#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Базовый класс для интеграции с LLM
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import logging
import time

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Результат работы LLM"""
    text: str
    model: str
    tokens_used: int
    cost: float
    processing_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Базовый класс для LLM провайдеров"""
    
    @abstractmethod
    def analyze(self, text: str, prompt: str) -> Dict[str, Any]:
        pass
