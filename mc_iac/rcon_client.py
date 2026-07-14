from mcrcon import MCRcon


class RconClient:
    def __init__(self, host="localhost", password="changeme123", port=25575):
        self.host = host
        self.password = password
        self.port = port

    def run(self, command: str) -> str:
        """Run a single command on its own connection."""
        with MCRcon(self.host, self.password, port=self.port) as mcr:
            return mcr.command(command)

    def run_many(self, commands: list[str]) -> list[str]:
        """
        Run many commands over ONE connection. Structures like the farm
        and path generate hundreds of setblock commands; opening a fresh
        RCON connection per command makes applies painfully slow.
        """
        responses = []
        with MCRcon(self.host, self.password, port=self.port) as mcr:
            for command in commands:
                responses.append(mcr.command(command))
        return responses
