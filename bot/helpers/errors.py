from discord.app_commands import AppCommandError
from discord import Member


class CustomError(AppCommandError):
    """ A custom error that is raised when a command encountres an issue. """

    def __init__(self, message: str=None):
        if not message:
            message = "Unknown error occurred."
        self.message = message
        super().__init__(message)


class APIError(AppCommandError):
    """ A custom error that is raised when a command encountres an issue with API. """

    def __init__(self, message: str=None):
        if not message:
            message = "Something went wrong with API call."
        self.message = message
        super().__init__(message)


class JoinLobbyError(ValueError):
    """ Raised when a player can't join lobby for some reason. """

    def __init__(self, user: Member, reason: str):
        """ Set message parameter. """
        self.message = f"Unable to add **{user.display_name}**: " + reason
