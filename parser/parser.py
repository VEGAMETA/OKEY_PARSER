from abc import ABC, abstractmethod


class BaseParser(ABC):
    """
    Abstract parser class
    """

    @abstractmethod
    def parse(self): ...
