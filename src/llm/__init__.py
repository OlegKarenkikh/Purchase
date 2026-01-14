#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль LLM интеграции для АИС УДЗ
"""

from .base_llm import BaseLLM, LLMResponse
from .claude_client import ClaudeClient

__all__ = ["BaseLLM", "ClaudeClient"]
