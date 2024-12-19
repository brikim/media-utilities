import requests
import json

class JellystatServer:
    def __init__(self, url, api_key, logger):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.logger = logger

    def get_api_url(self):
        return self.url + '/api'
    
    def get_user_watch_history(self, userId):
        try:
            headers = {
                'x-api-token': self.api_key,
                "Content-Type": "application/json"}
            payload = {
                'userid': userId}
            r = requests.post(self.get_api_url() + '/getUserHistory', headers=headers, data=json.dumps(payload))
            return r.json()
        except Exception as e:
            self.logger.error("{}: Error getting user history ERROR: {}".format(self.__module__, e))