def greet(name: str) -> str:
    return f"Hello {name}"


class Greeter:
    def __init__(self, name: str):
        self.name = name

    def greet(self) -> str:
        return f"Hello {self.name}"
