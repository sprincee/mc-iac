from abc import ABC, abstractmethod

class Resource(ABC):
    """Base class for anything mc-iac can provision."""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config

    @abstractmethod
    def create_commands(self) -> list[str]:
        """Return RCON commands needed to create this resource."""
        ...

    @abstractmethod
    def destroy_commands(self) -> list[str]:
        """Return RCON commands needed to remove this resource."""
        ...

    @abstractmethod
    def fingerprint(self) -> str:
        """Return a hash/string representing this resource's desired state,
        used to detect drift/changes between spec and state."""
        ...