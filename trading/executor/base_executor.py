from abc import ABC, abstractmethod

class BaseExecutor(ABC):
    @abstractmethod
    def buy(self, stock_code: str, volume: int) -> str:
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def get_data_api(self):
        pass
