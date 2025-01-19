import requests
import json
from common.utils import get_tautulli_ansi_code, get_log_header, get_tag

class TautulliAPI:
    def __init__(self, url, api_key, logger):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.logger = logger
        self.invalid_user_id = 0
        self.valid = False
        self.log_header = get_log_header(get_tautulli_ansi_code(), self.__module__)
        
        try:
            payload = {
                'apikey': self.api_key,
                'cmd': 'get_tautulli_info'}
            r = requests.get(self.get_api_url(), params=payload)
            if r.status_code < 300:
                self.valid = True
            else:
                self.logger.warning('{} could not connect to service {}'.format(self.log_header, get_tag('status_code', r.status_code)))
        except Exception as e:
            self.logger.error('{} connection {}'.format(self.log_header, get_tag('error', e)))
            self.valid = False

    def get_valid(self):
        return self.valid
    
    def get_media_type_episode_name(self):
        return 'episode'
    
    def get_media_type_movie_name(self):
        return 'movie'
    
    def get_invalid_user_id(self):
        return self.invalid_user_id
    
    def get_api_url(self):
        return self.url + '/api/v2'
    
    def get_library_id(self, lib_name):
        try:
            payload = {
                'apikey': self.api_key,
                'cmd': 'get_libraries'}

            r = requests.get(self.get_api_url(), params=payload)
            response = r.json()
            for lib in response['response']['data']:
                if (lib['section_name'] == lib_name):
                    return lib['section_id']
        except Exception as e:
            self.logger.error("{} get_library_id {} {}".format(self.log_header, get_tag('library', lib_name), get_tag('error', e)))
            
        return '0'
            
    def get_user_id(self, user_name):
        payload = {
            'apikey': self.api_key,
            'cmd': 'get_users'}

        try:
            r = requests.get(self.get_api_url(), params=payload)
            response = r.json()
            for userData in response['response']['data']:
                if userData['username'] == user_name:
                    return userData['user_id']
        except Exception as e:
            self.logger.error("{} get_user_id {} {}".format(self.log_header, get_tag('user', user_name), get_tag('error', e)))

        return self.invalid_user_id
    
    def get_watch_history_for_user(self, user_id, dateTimeStringForHistory):
        payload = {
            'apikey': self.api_key,
            'cmd': 'get_history',
            'include_activity': 0,
            'user_id': user_id,
            'after': dateTimeStringForHistory}

        try:
            r = requests.get(self.get_api_url(), params=payload)
            response = r.json()
            return response['response']['data']['data']
        except Exception as e:
            self.logger.error("{} get_watch_history_for_user {} {}".format(self.log_header, get_tag('user_id', user_id), get_tag('error', e)))
            
    def get_watch_history_for_user_and_library(self, user_id, lib_id, dateTimeStringForHistory):
        payload = {
            'apikey': self.api_key,
            'cmd': 'get_history',
            'include_activity': 0,
            'user_id': user_id,
            'section_id': lib_id,
            'after': dateTimeStringForHistory}

        try:
            r = requests.get(self.get_api_url(), params=payload)
            response = r.json()
            return response['response']['data']['data']
        except Exception as e:
            self.logger.error("{} get_watch_history_for_user_and_library {} {} {}".format(self.log_header, get_tag('user_id', user_id), get_tag('library_id', lib_id), get_tag('error', e)))
            
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
            self.logger.error("{} get_filename {} {}".format(self.log_header, get_tag('key', key), get_tag('error', e)))
