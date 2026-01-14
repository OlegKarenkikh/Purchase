#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Менеджер кэширования результатов анализа
"""

import hashlib
import json
import pickle
from typing import Any, Optional
from pathlib import Path
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Менеджер для кэширования результатов анализа
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
            with open(cache_file, 'rb') as f:
                value = pickle.load(f)
            logger.debug(f"Кэш попадание: {key}")
            return value
        except Exception as e:
            logger.error(f"Ошибка чтения кэша: {e}")
            return None
    
    def set(self, key: str, value: Any) -> None:
        """
        Сохранение значения в кэш
        
        Args:
            key: Ключ
            value: Значение
        """
        cache_file = self._get_cache_file(key)
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(value, f)
            logger.debug(f"Кэш сохранен: {key}")
        except Exception as e:
            logger.error(f"Ошибка записи кэша: {e}")
    
    def clear(self) -> None:
        """Очистка всего кэша"""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
        logger.info("Кэш очищен")
    
    def _get_cache_file(self, key: str) -> Path:
        """Получение пути к файлу кэша"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    @staticmethod
    def generate_key(text: str, **kwargs) -> str:
        """
        Генерация ключа кэша
        
        Args:
            text: Текст документа
            **kwargs: Дополнительные параметры
            
        Returns:
            Ключ кэша
        """
        # Создаем хэш от текста и параметров
        data = {"text": text, **kwargs}
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
