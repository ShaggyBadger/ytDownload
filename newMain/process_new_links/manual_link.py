from rich.console import Console

class ManualLinkProcessor():
    def __init__(self):
        self.console = Console()

    def process_link(self):
        console = self.console
        console.clear()
        console.print("Processing Manual Link...", style="bold blue")
        link = console.input("Enter the link: ").strip()