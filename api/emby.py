import requests
from logging import Logger
from typing import Any
from common import utils

class EmbyAPI:
    def __init__(self, url: str, api_key: str, media_path: str, logger: Logger):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.media_path = media_path
        self.logger = logger
        self.invalid_item_id = '0'
        self.log_header = utils.get_log_header(utils.get_emby_ansi_code(), self.__module__)
    
    def __get_api_url(self) -> str:
        return self.url + '/emby'
    
    def get_valid(self) -> bool:
        try:
            payload = {'api_key': self.api_key}
            r = requests.get(self.__get_api_url() + '/System/Configuration', params=payload)
            if r.status_code < 300:
                return True
        except Exception as e:
            pass
        return False
    
    def get_name(self) -> str:
        try:
            payload = {'api_key': self.api_key}
            r = requests.get(self.__get_api_url() + '/System/Info', params=payload)
            response = r.json()
            return response['ServerName']
        except Exception as e:
            self.logger.error("{} get_name {}".format(self.log_header, utils.get_tag('error', e)))
        return self.invalid_item_id
    
    def get_connection_error_log(self) -> str:
        return 'Could not connect to {} server {} {}'.format(utils.get_formatted_emby(), utils.get_tag('url', self.url), utils.get_tag('api_key', self.api_key))
        
    def get_media_type_episode_name(self) -> str:
        return 'Episode'
    
    def get_media_type_movie_name(self) -> str:
        return 'Movie'
    
    def get_media_path(self) -> str:
        return self.media_path
    
    def get_invalid_item_id(self) -> str:
        return self.invalid_item_id
    
    def get_user_id(self, userName) -> str:
        try:
            payload = {'api_key': self.api_key}
            r = requests.get(self.__get_api_url() + '/Users/Query', params=payload)
            response = r.json()
            
            for item in response['Items']:
                if item['Name'] == userName:
                    return item['Id']
        except Exception as e:
            self.logger.error("{} get_user_id {} {}".format(self.log_header, utils.get_tag('user', userName), utils.get_tag('error', e)))

        self.logger.warning("{} get_user_id no user found {}".format(self.log_header, utils.get_tag('user', userName)))
        return self.invalid_item_id
    
    def search_item(self, id: str) -> Any:
        try:
            payload = {
            'api_key': self.api_key,
            'Ids': id,
            'Fields': 'Path'}
            
            r = requests.get(self.__get_api_url() + '/Items', params=payload)
            response = r.json()['Items']
            response_length = len(response)
            if response_length > 0:
                if (response_length > 1):
                    self.logger.warning('{} search_item returned multiple items {}'.format(self.log_header, utils.get_tag('item', id)))
                return response[0]
            else:
                self.logger.warning('{} search_item returned no results {}'.format(self.log_header, utils.get_tag('item', id)))
                return None
        except Exception as e:
            self.logger.error("{} search_item {} {}".format(self.log_header, utils.get_tag('item', id), utils.get_tag('error', e)))
    
    def get_item_id_from_path(self, path) -> str:
        try:
            payload = {
                'api_key': self.api_key,
                'Recursive': 'true',
                'Path': path,
                'Fields': 'Path'}
            r = requests.get(self.__get_api_url() + '/Items', params=payload)
            response = r.json()

            if response['TotalRecordCount'] > 0:
                return response['Items'][0]['Id']
            
        except Exception as e:
            self.logger.error("{} get_item_id_from_path {} {}".format(self.log_header, utils.get_tag('path', path), utils.get_tag('error', e)))
            
        return self.get_invalid_item_id()
    
    def get_watched_status(self, user_id: str, item_id: str) -> bool:
        try:
            payload = {
            'api_key': self.api_key,
            'Ids': item_id,
            'IsPlayed': 'true'}
            
            r = requests.get(self.__get_api_url() + '/Users/' + user_id + '/Items', params=payload)
            if r.status_code < 300:
                return r.json()['TotalRecordCount'] > 0
            else:
                self.logger.error('{} get_watched_status api response error {} {} {} {}'.format(self.log_header, utils.get_tag('code', r.status_code), utils.get_tag('user', user_id), utils.get_tag('item', item_id), utils.get_tag('error', r.reason)))
                return False
        except Exception as e:
            self.logger.error("{} get_watched_status failed for {} {} {}".format(self.log_header, utils.get_tag('user', user_id), utils.get_tag('item', item_id), utils.get_tag('error', e)))
            
        return False
    
    def set_watched_item(self, user_id: str, item_id: str):
        try:
            headers = {'accept': 'application/json'}
            embyUrl = self.__get_api_url() + '/Users/' + user_id + '/PlayedItems/' + item_id + '?api_key=' + self.api_key
            requests.post(embyUrl, headers=headers)
        except Exception as e:
            self.logger.error("{} set_watched_item {} {} {}".format(self.log_header, utils.get_tag('user', user_id), utils.get_tag('item', item_id), utils.get_tag('error', e)))
    
    def set_library_scan(self, library_id: str):
        try:
            headers = {'accept': 'application/json'}
            payload = {
                'api_key': self.api_key,
                'Recursive': 'true',
                'ImageRefreshMode': 'Default',
                'MetadataRefreshMode': 'Default',
                'ReplaceAllImages': 'false',
                'ReplaceAllMetadata': 'false'}
            embyUrl = self.__get_api_url() + '/Items/' + library_id + '/Refresh'
            requests.post(embyUrl, headers=headers, params=payload)
        except Exception as e:
            self.logger.error("{} set_library_scan {}".format(self.log_header, utils.get_tag('error', e)))
    
    def get_library_from_name(self, name: str) -> Any:
        try:
            payload = {'api_key': self.api_key}
            r = requests.get(self.__get_api_url() + '/Library/SelectableMediaFolders', params=payload)
            response = r.json()

            for library in response:
                if library['Name'] == name:
                    return library
        except Exception as e:
            self.logger.error("{} get_library_from_name {}".format(self.log_header, utils.get_tag('error', e)))
        
        self.logger.warning("{} get_library_from_name no library found with {}".format(self.log_header, utils.get_tag('name', name)))
        return self.invalid_item_id
    
    def get_library_id(self, name: str) -> Any:
        try:
            payload = {'api_key': self.api_key}
            r = requests.get(self.__get_api_url() + '/Library/SelectableMediaFolders', params=payload)
            response = r.json()

            for library in response:
                if library['Name'] == name:
                    return library['Id']
        except Exception as e:
            pass
        
        return self.invalid_item_id
