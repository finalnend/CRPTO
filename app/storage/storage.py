"""Storage service interfaces and implementations.

Provides abstract storage interface and JSON file-based implementation
for persisting application state.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class IStorageService(ABC):
    """Abstract base class for storage services.
    
    Defines the interface for saving, loading, and deleting data
    with string keys.
    """

    @abstractmethod
    def save(self, key: str, data: Any) -> None:
        """Save data with the given key.
        
        Args:
            key: Unique identifier for the data
            data: JSON-serializable data to store
        """
        ...

    @abstractmethod
    def load(self, key: str) -> Optional[Any]:
        """Load data for the given key.
        
        Args:
            key: Unique identifier for the data
            
        Returns:
            The stored data, or None if not found
        """
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete data for the given key.
        
        Args:
            key: Unique identifier for the data to delete
        """
        ...


class JsonFileStorage(IStorageService):
    """JSON file-based storage implementation.
    
    Stores each key as a separate JSON file in the specified base directory.
    Uses pathlib for cross-platform file path handling.
    """

    def __init__(self, base_path: str | Path) -> None:
        """Initialize the JSON file storage.
        
        Args:
            base_path: Directory path where JSON files will be stored
        """
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, key: str) -> Path:
        """Get the file path for a given key.
        
        Args:
            key: Storage key
            
        Returns:
            Path to the JSON file for this key
        """
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self._base_path / f"{safe_key}.json"

    def save(self, key: str, data: Any) -> None:
        """Save data to a JSON file.
        
        Args:
            key: Unique identifier for the data
            data: JSON-serializable data to store
            
        Raises:
            TypeError: If data is not JSON-serializable
            OSError: If file cannot be written
        """
        file_path = self._get_file_path(key)
        try:
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except (TypeError, OSError) as e:
            logger.error(f"Failed to save data for key '{key}': {e}")
            raise

    def load(self, key: str) -> Optional[Any]:
        """Load data from a JSON file.
        
        Args:
            key: Unique identifier for the data
            
        Returns:
            The stored data, or None if file doesn't exist or is corrupted
        """
        file_path = self._get_file_path(key)
        if not file_path.exists():
            return None
        
        try:
            with file_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted data for key '{key}': {e}")
            return None
        except OSError as e:
            logger.error(f"Failed to load data for key '{key}': {e}")
            return None

    def delete(self, key: str) -> None:
        """Delete a JSON file for the given key.
        
        Args:
            key: Unique identifier for the data to delete
        """
        file_path = self._get_file_path(key)
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError as e:
            logger.error(f"Failed to delete data for key '{key}': {e}")
