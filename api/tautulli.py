import requests
import json

class TautulliServer:
    def __init__(self, url, api_key, logger):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.logger = logger

    def get_api_url(self):
        return self.url + '/api/v2'
    
    def get_library_id(self, libName):
        try:
            payload = {
                'apikey': self.api_key,
                'cmd': 'get_libraries'}

            r = requests.get(self.get_api_url(), params=payload)
            response = r.json()
            for lib in response['response']['data']:
                if (lib['section_name'] == libName):
                    return lib['section_id']
        except Exception as e:
            self.logger.error("{}: Get Plex Library Id({}) ERROR:{}".format(self.__module__, libName, e))
            
        return '0'
            
    def get_user_id(self, userName):
        payload = {
            'apikey': self.api_key,
            'cmd': 'get_users'}

        try:
            r = requests.get(self.get_api_url(), params=payload)
            response = r.json()
            for userData in response['response']['data']:
                if userData['username'] == userName:
                    return userData['user_id']
        except Exception as e:
            self.logger.error("{}: Get Plex Users({}) ERROR:{}".format(self.__module__, userName, e))

        return 0
    
    def get_watch_history_for_user(self, userId, dateTimeStringForHistory):
        payload = {
            'apikey': self.api_key,
            'cmd': 'get_history',
            'include_activity': 0,
            'user_id': userId,
            'after': dateTimeStringForHistory}

        try:
            r = requests.get(self.get_api_url(), params=payload)
            response = r.json()
            return response['response']['data']['data']
        except Exception as e:
            self.logger.error("{}: Get Watch Status ERROR:{}".format(self.__module__, e))
            
    def get_watch_history_for_user_and_library(self, userId, libId, dateTimeStringForHistory):
        payload = {
            'apikey': self.api_key,
            'cmd': 'get_history',
            'include_activity': 0,
            'user_id': userId,
            'section_id': libId,
            'after': dateTimeStringForHistory}

        try:
            r = requests.get(self.get_api_url(), params=payload)
            response = r.json()
            return response['response']['data']['data']
        except Exception as e:
            self.logger.error("{}: Get Watch Status ERROR:{}".format(self.__module__, e))
            
    def get_filename(self, key):
        try:
            payload = {
                'apikey': self.api_key,
                'rating_key': str(key),
                'cmd': 'get_metadata'}
            r = requests.get(self.get_api_url(), params=payload)
            response = r.json()

            res_data = response['response']['data']
            if (len(res_data) > 0):
                return res_data['media_info'][0]['parts'][0]['file']
            else:
                return ""

        except Exception as e:
            self.logger.error("{}: Tautulli API 'get_metadata' request failed: {}.\n".format(self.__module__, e))