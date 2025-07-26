from abc import ABC, abstractmethod

class AbstractEmbeddingManager(ABC):

    @abstractmethod
    def index(self):
        pass

    @abstractmethod
    def clean(self):
        pass

    @abstractmethod
    def stats(self):
        pass
