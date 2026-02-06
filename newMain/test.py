#!/usr/bin/env python3

import time
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.align import Align

console = Console()

# CHANGE THIS to try different spinners
SPINNER_NAME = "point"  # examples: dots, line, pipe, simpleDots, star, bounce, growVertical, moon, earth

def main():
    spinner = Spinner(SPINNER_NAME, text=f"[bold cyan]Spinner: {SPINNER_NAME}")

    # Live continuously refreshes the spinner
    with Live(
        Align.center(spinner, vertical="middle"),
        refresh_per_second=30,
        console=console,
        screen=True,
    ):
        while True:
            time.sleep(0.1)  # keep alive forever


if __name__ == "__main__":
    main()
