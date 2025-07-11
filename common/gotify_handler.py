""" Gotify Log Handler """

import logging
import requests
from requests.exceptions import RequestException


class GotifyHandler(logging.Handler):
    """ Gotify Log Handler """

    def __init__(
        self,
        url,
        app_token,
        title,
        priority
    ):
        self.url = url.rstrip('/')
        self.app_token = app_token
        self.title = title
        self.priority = priority
        logging.Handler.__init__(self=self)

    def emit(self, record: logging.LogRecord):
        """ Emits a log record to Gotify """
        try:
            formatted_message = self.formatter.format(record)
            requests.post(
                f"{self.url}/message?token={self.app_token}",
                json={
                    "message": formatted_message,
                    "priority": self.priority,
                    "title": f"{self.title} - {record.levelname}"
                },
                timeout=5
            )
        except RequestException:
            self.handleError(record)
