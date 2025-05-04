""" Api Base """

from common.log_manager import LogManager
from common.utils import get_log_header


class ApiBase:
    """
    Base class for API interactions with media servers.
    Provides common functionality for API classes like setting up the URL,
    API key, ansi code, module name and LogManager
    """

    def __init__(
        self,
        server_name: str,
        url: str,
        api_key: str,
        ansi_code: str,
        module: str,
        log_manager: LogManager
    ):
        """
        Initializes the ApiBase with the server URL, API key, ANSI code, module name, and LogManager.

        Args:
            url (str): The base URL of the media server.
            api_key (str): The API key for authenticating with the server.
            ansi_code (str): The ANSI escape code for log header coloring.
            module (str): The name of the module using this class.
            log_manager (LogManager): The LogManager instance for logging messages.
        """

        self.server_name = server_name
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.log_manager = log_manager
        self.invalid_item_id = "0"
        self.invalid_item_type = None
        self.log_header = get_log_header(
            ansi_code, f"{module}({self.server_name})"
        )

    def get_valid(self) -> bool:
        """
        Checks if the connection to the media server is valid. (To be implemented by subclasses)
        """
        return False

    def get_server_name(self) -> str:
        """
        Retrieves the server name
        """
        return self.server_name

    def get_server_reported_name(self) -> str:
        """
        Retrieves the friendly name of the media server. (To be implemented by subclasses)
        """
        return ""
