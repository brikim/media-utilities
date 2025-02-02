import requests
from logging import Logger
from typing import Any
from common.utils import get_tautulli_ansi_code, get_log_header, get_tag, get_formatted_tautulli

class TautulliAPI:
    def __init__(self, url: str, api_key: str, logger: Logger):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.logger = logger
        self.item_invalid_type = None
        self.log_header = get_log_header(get_tautulli_ansi_code(), self.__module__)

    def get_valid(self) -> bool:
        try:
            payload = {
                'apikey': self.api_key,
                'cmd': 'get_tautulli_info'}
            r = requests.get(self.get_api_url(), params=payload)
            if r.status_code < 300:
                return True
        except Exception as e:
            pass
        return False
    
    def get_connection_error_log(self) -> str:
        return 'Could not connect to {} {} {}'.format(get_formatted_tautulli(), get_tag('url', self.url), get_tag('api_key', self.api_key))
    
    def get_media_type_episode_name(self) -> str:
        return 'episode'
    
    def get_media_type_movie_name(self) -> str:
        return 'movie'
    
    def get_invalid_item(self) -> Any:
        return self.item_invalid_type
    
    def get_api_url(self) -> str:
        return self.url + '/api/v2'
    
    def get_library_id(self, lib_name: str) -> str:
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
            
    def get_user_id(self, user_name: str) -> str:
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

        return self.get_invalid_item()
    
    def get_user_info(self, user_name: str) -> Any:
        payload = {
            'apikey': self.api_key,
            'cmd': 'get_users_table'}

        try:
            r = requests.get(self.get_api_url(), params=payload)
            response = r.json()
            for user_info in response['response']['data']['data']:
                if user_info['username'] == user_name:
                    return user_info
        except Exception as e:
            self.logger.error("{} get_user_info {} {}".format(self.log_header, get_tag('user', user_name), get_tag('error', e)))

        return self.get_invalid_item()
    
    def get_watch_history_for_user(self, user_id: str, dateTimeStringForHistory: str) -> Any:
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
            
    def get_watch_history_for_user_and_library(self, user_id: str, lib_id: str, dateTimeStringForHistory: str) -> Any:
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
            
    def get_filename(self, key: Any) -> str:
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
