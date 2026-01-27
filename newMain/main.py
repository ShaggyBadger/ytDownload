"""Main entry point for the application."""
from controller.main import MainMenuController
from config import config

if __name__ == "__main__":
    #config.select_random_spinner()
    app = MainMenuController()
    app.run()
