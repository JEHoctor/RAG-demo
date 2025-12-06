class Logic:
    """Top-level application logic."""

    def __init__(self, username: str | None = None) -> None:
        """Initialize the application logic.

        This is quite skeletal for now but the intent is to separate application logic from the UI where beneficial.

        Args:
            username (str | None, optional): The username provided as a command line argument. Defaults to None.
        """
        self.username = username
