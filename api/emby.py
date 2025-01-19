import requests
import json
from common.utils import get_tag, get_log_header, get_emby_ansi_code

class EmbyAPI:
    def __init__(self, url, api_key, media_path, logger):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.media_path = media_path
        self.logger = logger
        self.invalid_item_id = '0'
        self.valid = False
        self.log_header = get_log_header(get_emby_ansi_code(), self.__module__)
        
        try:
            payload = {'api_key': self.api_key}
            r = requests.get(self.get_api_url() + '/System/Configuration', params=payload)
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
        return 'Episode'
    
    def get_media_type_movie_name(self):
        return 'Movie'
    
    def get_media_path(self):
        return self.media_path
    
    def get_invalid_item_id(self):
        return self.invalid_item_id
    
    def get_api_url(self):
        return self.url + '/emby'
    
    def get_user_id(self, userName):
        try:
            payload = {'api_key': self.api_key}
            r = requests.get(self.get_api_url() + '/Users/Query', params=payload)
            response = r.json()
            
            for item in response['Items']:
                if item['Name'] == userName:
                    return item['Id']
        except Exception as e:
            self.logger.error("{} get_user_id {} {}".format(self.log_header, get_tag('user', userName), get_tag('error', e)))

        self.logger.warning("{} get_user_id no user found {}".format(self.log_header, get_tag('user', userName)))
        return self.invalid_item_id
    
    def search_item(self, id):
        try:
            payload = {
            'api_key': self.api_key,
            'Ids': id,
            'Fields': 'Path'}
            
            r = requests.get(self.get_api_url() + '/Items', params=payload)
            response = r.json()['Items']
            response_length = len(response)
            if response_length > 0:
                if (response_length > 1):
                    self.logger.warning('{} search_item returned multiple items {}'.format(self.log_header, get_tag('item', id)))
                return response[0]
            else:
                self.logger.warning('{} search_item returned no results {}'.format(self.log_header, get_tag('item', id)))
                return None
        except Exception as e:
            self.logger.error("{} search_item {} {}".format(self.log_header, get_tag('item', id), get_tag('error', e)))
    
    def get_item_id_from_path(self, path):
        try:
            payload = {
                'api_key': self.api_key,
                'Recursive': 'true',
                'Path': path,
                'Fields': 'Path'}
            r = requests.get(self.get_api_url() + '/Items', params=payload)
            response = r.json()

            if response['TotalRecordCount'] > 0:
                return response['Items'][0]['Id']
            
        except Exception as e:
            self.logger.error("{} get_item_id_from_path {} {}".format(self.log_header, get_tag('path', path), get_tag('error', e)))
            
        return self.get_invalid_item_id()
    
    def get_watched_status(self, user_id, item_id):
        try:
            payload = {
            'api_key': self.api_key,
            'Ids': item_id,
            'IsPlayed': 'true'}
            
            r = requests.get(self.get_api_url() + '/Users/' + user_id + '/Items', params=payload)
            if r.status_code < 300:
                return r.json()['TotalRecordCount'] > 0
            else:
                self.logger.error('{} get_watched_status api response error {} {} {} {}'.format(self.log_header, get_tag('code', r.status_code), get_tag('user', user_id), get_tag('item', item_id), get_tag('error', r.reason)))
                return None
        except Exception as e:
            self.logger.error("{} get_watched_status failed for {} {} {}".format(self.log_header, get_tag('user', user_id), get_tag('item', item_id), get_tag('error', e)))
            
        return False
    
    def set_watched_item(self, user_id, item_id):
        try:
            headers = {'accept': 'application/json'}
            embyUrl = self.get_api_url() + '/Users/' + user_id + '/PlayedItems/' + item_id + '?api_key=' + self.api_key
            requests.post(embyUrl, headers=headers)
        except Exception as e:
            self.logger.error("{} set_watched_item {} {} {}".format(self.log_header, get_tag('user', user_id), get_tag('item', item_id), get_tag('error', e)))
    
    def set_library_scan(self, library_id):
        try:
            headers = {'accept': 'application/json'}
            payload = {
                'api_key': self.api_key,
                'Recursive': 'true',
                'ImageRefreshMode': 'Default',
                'MetadataRefreshMode': 'Default',
                'ReplaceAllImages': 'false',
                'ReplaceAllMetadata': 'false'}
            embyUrl = self.get_api_url() + '/Items/' + library_id + '/Refresh'
            requests.post(embyUrl, headers=headers, params=payload)
        except Exception as e:
            self.logger.error("{} set_library_scan {}".format(self.log_header, get_tag('error', e)))
    
    def get_library_from_name(self, name):
        try:
            payload = {'api_key': self.api_key}
            r = requests.get(self.get_api_url() + '/Library/SelectableMediaFolders', params=payload)
            response = r.json()

            for library in response:
                if library['Name'] == name:
                    return library
        except Exception as e:
            self.logger.error("{} get_library_from_name {}".format(self.log_header, get_tag('error', e)))
        
        self.logger.warning("{} get_library_from_name no library found with {}".format(self.log_header, get_tag('name', name)))
        return self.invalid_item_id
