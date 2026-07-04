from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class CliCommand(ABC):
    """
    Интерфейс консольной команды или группы

    """

    _key = None
    _parent = None

    @property
    def parent(self) -> CliCommand | None:
        return self._parent

    @parent.setter
    def parent(self, parent: CliCommand | None):
        self._parent = parent

    @property
    def key(self) -> list[str]:
        return self._key or []

    @key.setter
    def key(self, key) -> None:
        self._key = key

    def add(self, command) -> None:
        pass

    def remove(self, command) -> None:
        pass

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """
        Базовый Компонент может сам реализовать некоторое поведение по умолчанию
        или поручить это конкретным классам, объявив метод, содержащий поведение
        абстрактным.
        """
        pass
