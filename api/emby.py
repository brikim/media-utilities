import requests
import json
from common.utils import remove_year_from_name
class EmbyAPI:
    def __init__(self, url, api_key, media_path, logger):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.media_path = media_path
        self.logger = logger
        self.invalid_item_id = '0'
    
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
            self.logger.error("{}: Get Emby Users({}) ERROR:{}".format(self.__module__, userName, e))

        return self.invalid_item_id
    
    def search(self, searchString, mediaType):
        try:
            payload = {
            'api_key': self.api_key,
            'Recursive': 'true',
            'SearchTerm': searchString,
            'IncludeItemTypes': mediaType,
            'Fields': 'Path'}
            
            r = requests.get(self.get_api_url() + '/Items', params=payload)
            response = r.json()
            
            return response['Items']
        except Exception as e:
            self.logger.error("{}: Get Emby Search {} ERROR:{}".format(self.__module__, searchString, e))
    
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
                    self.logger.warning('{}: item id {} search returned multiple items'.format(self.__module__, id))
                return response[0]
            else:
                self.logger.warning('{}: item id {} returned no results'.format(self.__module__, id))
                return None
        except Exception as e:
            self.logger.error("{}: Get Emby Item {} ERROR:{}".format(self.__module__, id, e))
            
    def search_all(self, searchString):
        try:
            payload = {
            'api_key': self.api_key,
            'Recursive': 'true',
            'SearchTerm': searchString,
            'Fields': 'Path'}
            
            r = requests.get(self.get_api_url() + '/Items', params=payload)
            return r.json()['Items']
        except Exception as e:
            self.logger.error("{}: Get Emby Search {} ERROR:{}".format(self.__module__, searchString, e))
            
    def get_series_id(self, series_name, series_path):
        # Remove any year from the series name ... example (2017)
        cleaned_series_name = remove_year_from_name(series_name)
        cleaned_series_name = cleaned_series_name.lower()

        try:
            search_items = self.search(cleaned_series_name, 'Series')
            for item in search_items:
                if series_path == item['Path']:
                    return item['Id']
        except Exception as e:
            self.logger.error("{}: Get Emby Series Items({}) ERROR:{}".format(self.__module__, series_name, e))
            
        # return an invalid id if not found
        return self.invalid_item_id
    
    def get_series_episodes(self, series_id, season_num):
        try:
            payload = {
            'api_key': self.api_key,
            'Recursive': 'true',
            'Id': series_id,
            'Season': season_num,
            'Fields': 'Path'}
            
            r = requests.get(self.get_api_url() + '/Shows/' + series_id + '/Episodes', params=payload)
            return r.json()['Items']
        except Exception as e:
            self.logger.error("{}: Get Emby Series Episodes {} ERROR:{}".format(self.__module__, series_id, e))
    
    def get_series_episode_id(self, series_name, series_path, season_num, episode_path):
        series_id = self.get_series_id(series_name, series_path)
        if series_id != self.invalid_item_id:
            series_episodes = self.get_series_episodes(series_id, season_num)
            for episode in series_episodes:
                if episode['Path'] == episode_path:
                    return episode['Id']
        
        return self.invalid_item_id
    
    def get_movie_item_id(self, name, path):
        try:
            searchItems = self.search(name, 'Movie')
            for item in searchItems:
                if path == item['Path']:
                    return item['Id']
        except Exception as e:
            self.logger.error("{}: Get Emby Movie Items({}) ERROR:{}".format(self.__module__, name, e))

        # return an invalid id if not found
        return self.invalid_item_id
    
    def get_watched_status(self, userName, itemId):
        payload = {
            'api_key': self.api_key,
            'id': itemId}
        r = requests.get(self.get_api_url() + '/user_usage_stats/get_item_stats', params=payload)
        response = r.json()
        for userActivity in response:
            if userActivity['name'] == userName and userActivity['played'] == 'True':
                return True
        return False
    
    def set_watched_item(self, userId, itemId):
        try:
            headers = {'accept': 'application/json'}
            embyUrl = self.get_api_url() + '/Users/' + userId + '/PlayedItems/' + itemId + '?api_key=' + self.api_key
            requests.post(embyUrl, headers=headers)
        except Exception as e:
            self.logger.error("{}: Set Emby watched ERROR:{}".format(self.__module__, e))
            
    def set_all_library_scan(self):
        try:
            embyRefreshUrl = self.get_api_url() + '/Library/Refresh?api_key=' + self.api_key
            requests.post(embyRefreshUrl)
        except Exception as e:
            self.logger.error("{}: Set Emby library refresh ERROR:{}".format(self.__module__, e))
    
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
            self.logger.error("{}: Set Emby watched ERROR:{}".format(self.__module__, e))
        
    def get_library_from_path(self, path):
        try:
            payload = {'api_key': self.api_key}
            r = requests.get(self.get_api_url() + '/Library/SelectableMediaFolders', params=payload)
            response = r.json()

            for library in response:
                for subfolder in library['SubFolders']:
                    if subfolder['Path'] == path:
                        return library
        except Exception as e:
            self.logger.error("{}: Get library name from path ERROR:{}".format(self.__module__, e))
        
        self.logger.warning("{}: Emby does not contain a library with path {}".format(self.__module__, path))
        return ''
    
    def get_library_from_name(self, name):
        try:
            payload = {'api_key': self.api_key}
            r = requests.get(self.get_api_url() + '/Library/SelectableMediaFolders', params=payload)
            response = r.json()

            for library in response:
                if library['Name'] == name:
                    return library
        except Exception as e:
            self.logger.error("{}: Get library name from name ERROR:{}".format(self.__module__, e))
        
        self.logger.warning("{}: Emby does not contain a library with name {}".format(self.__module__, name))
        return ''
