from rich.align import Align
from rich.text import Text

class Menu():
    def __init__(self, console):
        self.console = console

    def build_menu_options(self):
        options = {
            '1': {
                'label': 'Read From CSV File',
                'action': 'csv_links'
                },
            '2': {
                'label': 'Manually Enter Link',
                'action': 'manual_link'
                },
            'b': {
                'label': 'Back to Main Menu',
                'action': 'back'
                }
        }
        return options

    def run(self):
        console = self.console

        while True:
            console.clear()
            
            title = Text("Process Links Menu", style="bold magenta")
            title = Align.center(title)
            subtitle = Text("Select an option to proceed.", style="dim")
            subtitle = Align.center(subtitle)

            menu_options = self.build_menu_options()
            menu_text = Text()
            for key, value in menu_options.items():
                menu_text.append(f"{key}", style="bold green")
                menu_text.append(f" : {value.get('label')}\n", style="bold white")
            
            input_prompt = Text("Enter your choice: ", style="bold yellow")

            console.print(title)
            console.print(subtitle)
            console.print(menu_text)

            selection = console.input(input_prompt).strip().lower()
            if selection in menu_options:
                selected_dict = menu_options.get(selection)
                selected_action = selected_dict.get('action')
                return selected_action