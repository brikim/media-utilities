import requests
import json

class JellystatAPI:
    def __init__(self, url, api_key, logger):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.logger = logger

    def get_api_url(self):
        return self.url + '/api'
    
    def get_headers(self):
        return {'x-api-token': self.api_key,
                "Content-Type": "application/json"}
        
    def get_library_id(self, libName):
        try:
            payload = {}
            r = requests.get(self.get_api_url() + '/getLibraries', headers=self.get_headers(), params=payload)
            response = r.json()
            for lib in response:
                if lib['Name'] == libName:
                    return lib['Id']
        except Exception as e:
            self.logger.info("{}: Error getting library id ({}) Error: {}.\n".format(self.__module__, libName, e))
            
        return '0'
        
    def get_user_watch_history(self, userId):
        try:
            payload = {
                'userid': userId}
            r = requests.post(self.get_api_url() + '/getUserHistory', headers=self.get_headers(), data=json.dumps(payload))
            
            response = r.json()
            if 'results' in response:
                return response['results']
            else:
                return response
        except Exception as e:
            self.logger.error("{}: Error getting user history ERROR: {}".format(self.__module__, e))
            
    def get_library_history(self, libId):
        try:
            payload = {
                'libraryid': libId}
            r = requests.post(self.get_api_url() + '/getLibraryHistory', headers=self.get_headers(), data=json.dumps(payload))
            
            response = r.json()
            if 'results' in response:
                return response['results']
            else:
                return response
        except Exception as e:
            self.logger.error("{}: Error getting library history ERROR: {}".format(self.__module__, e))
            
    def get_item_details(self, itemId):
        try:
            payload = {'Id': itemId}
            r = requests.post(self.get_api_url() + '/getItemDetails', headers=self.get_headers(), data=json.dumps(payload))
            return r.json()
        except Exception as e:
            self.logger.error("{}: Error getting item details ERROR: {}".format(self.__module__, e))