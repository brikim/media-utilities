import requests
import json

from common.utils import get_tag, get_log_header, get_jellystat_ansi_code
class JellystatAPI:
    def __init__(self, url, api_key, logger):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.logger = logger
        self.valid = False
        self.log_header = get_log_header(get_jellystat_ansi_code(), self.__module__)
        
        try:
            payload = {}
            r = requests.get(self.get_api_url() + '/getconfig', headers=self.get_headers(), params=payload)
            if r.status_code < 300:
                self.valid = True
            else:
                self.logger.warning('{} could not connect to service {}'.format(self.log_header, get_tag('status_code', r.status_code)))
        except Exception as e:
            self.logger.error('{} connection {}'.format(self.log_header, get_tag('error', e)))
            self.valid = False
        
    def get_valid(self):
        return self.valid
    
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
            self.logger.error("{} get_library_id {} {}".format(self.log_header, get_tag('library_id', libName), get_tag('error', e)))
            
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
            self.logger.error("{} get_user_watch_history {} {}".format(self.log_header, get_tag('user_id', userId), get_tag('error', e)))
            
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
            self.logger.error("{} get_library_history {} {}".format(self.log_header, get_tag('lib_id', libId), get_tag('error', e)))
            
    def get_item_details(self, itemId):
        try:
            payload = {'Id': itemId}
            r = requests.post(self.get_api_url() + '/getItemDetails', headers=self.get_headers(), data=json.dumps(payload))
            return r.json()
        except Exception as e:
            self.logger.error("{} get_item_details {} {}".format(self.log_header, get_tag('item', itemId), get_tag('error', e)))
