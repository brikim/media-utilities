
import requests
import logging

class GotifyHandler(logging.Handler):
    def __init__(self, url, app_token, priority):
        self.url = url.rstrip('/')
        self.app_token = app_token
        self.priority = priority
        logging.Handler.__init__(self=self)

    def emit(self, record):
        try:
            requests.post(self.url + '/message?token=' + self.app_token, json={
                        "message": record.message,
                        "priority": self.priority,
                        "title": "Media-Utility " + record.levelname})
        except:
            self.handleError(record)
