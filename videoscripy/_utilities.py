from colorama import init


init()

colorAnsi = {
    "reset": "\x1b[0m",
    "red": "\x1b[31m",
    "green": "\x1b[32m",
    "yellow": "\x1b[33m",
    "blue": "\x1b[34m",
}


def printC(text: str, color: str | None = None) -> None:
    """Print text in one of the supported ANSI colors."""
    if color is None:
        print(text)
        return

    try:
        ansi = colorAnsi[color]
    except KeyError:
        raise ValueError(f"Unsupported color: {color!r}") from None

    print(f"{ansi}{text}{colorAnsi['reset']}")
