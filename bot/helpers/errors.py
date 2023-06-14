from discord.app_commands import AppCommandError


class CustomError(AppCommandError):
    """ A custom error that is raised when a command encountres an issue. """

    def __init__(self, message):
        self.message = "Error: " + message
        super().__init__(message)


class APIError(AppCommandError):
    """ A custom error that is raised when a command encountres an issue with API. """

    def __init__(self, message):
        self.message = "API Error: " + message
        super().__init__(message)
