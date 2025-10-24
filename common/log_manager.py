""" Log Manager """

import logging
from logging import Logger
from logging.handlers import RotatingFileHandler
import sys

import colorlog

from common.gotify_handler import GotifyHandler
from common.gotify_plain_text_formatter import GotifyPlainTextFormatter
from common.plain_text_formatter import PlainTextFormatter


class LogManager:
    """
    Manages logging for the application, including file and console output,
    and optional Gotify notifications.
    """

    def __init__(
        self,
        log_name: str,
    ):
        """
        Initializes the LogManager with the specified log name.

        Args:
            log_name (str): The name of the logger.
        """
        self.logger = logging.getLogger(log_name)
        
        """ Create a logger for logging errors"""
        log_error_name = log_name + "_stderr";
        self.logger_error = logging.getLogger(log_error_name)
        
        self.handler_list: list[logging.Handler] = []
        self.error_handler_list: list[logging.Handler] = []

        # Set up the logger
        self.logger.setLevel(logging.INFO)
        self.file_formatter = PlainTextFormatter()

        # Create a file handler to write logs to a file
        self.file_rotating_handler = RotatingFileHandler(
            "/logs/media-utility.log", maxBytes=100000, backupCount=5
        )
        self.file_rotating_handler.setLevel(logging.INFO)
        self.file_rotating_handler.setFormatter(self.file_formatter)

        # Create a stream handler to print logs to the console
        self.console_info_handler = self.__create_color_log_handler(logging.INFO)
        self.console_error_handler = self.__create_color_log_handler(logging.WARNING);

        # Setup a place holder gotify handler
        self.gotify_handler: GotifyHandler = None
        self.gotify_formatter: GotifyPlainTextFormatter = None
        
        """ Add handles for INFO processing """
        self.logger.addHandler(self.file_rotating_handler)
        self.handler_list.append(self.file_rotating_handler)
        
        self.logger.addHandler(self.console_info_handler)
        self.handler_list.append(self.console_info_handler)
        
        """ Add handles for WARNING/ERROR processing """
        self.logger_error.addHandler(self.file_rotating_handler)
        self.error_handler_list.append(self.file_rotating_handler)
        
        self.logger_error.addHandler(self.console_error_handler)
        self.error_handler_list.append(self.console_error_handler)

    def __create_color_log_handler(self, log_level: int) -> logging.Handler:
        log_colors = {
            "DEBUG": "cyan",
            "INFO": "light_green",
            "WARNING": "light_yellow",
            "ERROR": "light_red",
            "CRITICAL": "bold_red",
        }
        log_date_format = "%Y-%m-%d %H:%M:%S"
        
        color_log_handler = colorlog.StreamHandler(sys.stdout if log_level == logging.INFO else sys.stderr)
        color_log_handler.setLevel(log_level)
        color_log_handler.setFormatter(
            colorlog.ColoredFormatter(
                "%(white)s%(asctime)s %(light_white)s- %(log_color)s%(levelname)s %(light_white)s- %(message)s",
                log_date_format,
                log_colors=log_colors,
            )
        )
        
        return color_log_handler
        
    def configure_gotify(self, config: dict) -> None:
        """Configures Gotify logging if enabled in the configuration."""
        # Create a Gotify log handler if set to log warnings
        # and errors to the Gotify instance
        if (
            "gotify_logging" in config
            and "enabled" in config["gotify_logging"]
            and config["gotify_logging"]["enabled"] == "True"
        ):
            if (
                "url" in config["gotify_logging"]
                and "app_token" in config["gotify_logging"]
                and "message_title" in config["gotify_logging"]
                and "priority" in config["gotify_logging"]
            ):
                self.gotify_formatter = GotifyPlainTextFormatter()
                self.gotify_handler = GotifyHandler(
                    config["gotify_logging"]["url"],
                    config["gotify_logging"]["app_token"],
                    config["gotify_logging"]["message_title"],
                    config["gotify_logging"]["priority"]
                )
                self.gotify_handler.setLevel(logging.WARNING)
                self.gotify_handler.setFormatter(self.gotify_formatter)

                """ Add handles for INFO processing """# Add the gotify handler to the logger
                self.logger.addHandler(self.gotify_handler)
                self.handler_list.append(self.gotify_handler)
                
                """ Add handles for WARNING/ERROR processing """# Add the gotify handler to the logger
                self.logger_error.addHandler(self.gotify_handler)
                self.error_handler_list.append(self.gotify_handler)
            else:
                self.logger.warning(
                    "Configuration gotify_logging enabled is True but missing an attribute url, app_token, message_title or priority"
                )

    def get_logger(self) -> Logger:
        """
        Returns the logger instance.

        Returns:
            Logger: The logger instance.
        """
        return self.logger

    def log_info(self, message: str):
        """ Log an info message. """
        self.logger.info(message)
        for handler in self.handler_list:
            handler.flush()

    def log_warning(self, message: str):
        """ Log an warning message. """
        self.logger_error.warning(message)
        for handler in self.error_handler_list:
            handler.flush()

    def log_error(self, message: str):
        """ Log an error message. """
        self.logger_error.error(message)
        for handler in self.error_handler_list:
            handler.flush()
