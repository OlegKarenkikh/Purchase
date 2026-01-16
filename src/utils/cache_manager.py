#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Менеджер кэширования результатов анализа

Безопасная реализация с использованием JSON и SHA-256.
"""

import hashlib
import json
from typing import Any, Optional, Dict
from pathlib import Path
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Менеджер для кэширования результатов анализа

    Использует JSON для сериализации (безопасно) и SHA-256 для хеширования ключей.
    """

    def __init__(self, cache_dir: str = ".cache", ttl_hours: int = 24):
        """
        Args:
            cache_dir: Директория для кэша
            ttl_hours: Время жизни кэша в часах
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)

    def get(self, key: str) -> Optional[Any]:
        """
        Получение значения из кэша

        Args:
            key: Ключ

        Returns:
            Значение или None если не найдено
        """
        cache_file = self._get_cache_file(key)

        if not cache_file.exists():
            return None

        # Проверка срока действия
        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - file_time > self.ttl:
            logger.debug(f"Кэш устарел: {key}")
            cache_file.unlink()
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                value = json.load(f)
            logger.debug(f"Кэш попадание: {key}")
            return value
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON кэша: {e}")
            cache_file.unlink(missing_ok=True)
            return None
        except Exception as e:
            logger.error(f"Ошибка чтения кэша: {e}")
            return None

    def set(self, key: str, value: Any) -> None:
        """
        Сохранение значения в кэш

        Args:
            key: Ключ
            value: Значение (должно быть JSON-сериализуемым)
        """
        cache_file = self._get_cache_file(key)

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(value, f, ensure_ascii=False, indent=2)
            logger.debug(f"Кэш сохранен: {key}")
        except TypeError as e:
            logger.error(f"Значение не сериализуемо в JSON: {e}")
        except Exception as e:
            logger.error(f"Ошибка записи кэша: {e}")

    def clear(self) -> None:
        """Очистка всего кэша"""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
        logger.info("Кэш очищен")

    def _get_cache_file(self, key: str) -> Path:
        """
        Получение пути к файлу кэша

        Использует SHA-256 для безопасного хеширования ключа.
        """
        # SHA-256 вместо MD5 для безопасности
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    @staticmethod
    def generate_key(text: str, **kwargs) -> str:
        """
        Генерация ключа кэша

        Args:
            text: Текст документа
            **kwargs: Дополнительные параметры

        Returns:
            Ключ кэша (SHA-256 хеш)
        """
        # Создаем хэш от текста и параметров
        data = {"text": text[:1000], **kwargs}  # Берем первые 1000 символов для ключа
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
