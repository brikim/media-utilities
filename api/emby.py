import requests
import json
from common.utils import remove_year_from_name, get_log_ansi_code, get_tag_ansi_code, get_emby_ansi_code
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
            self.logger.error("{}{}{}: get_user_id {}user={}{} {}error={}{}".format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), userName, get_tag_ansi_code(), get_log_ansi_code(), e))

        self.logger.warning("{}{}{}: get_user_id no user found {}user={}{}".format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), userName))
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
            self.logger.error("{}{}{}: search {}search={}{} {}error={}{}".format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), searchString, get_tag_ansi_code(), get_log_ansi_code(), e))
    
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
                    self.logger.warning('{}{}{}: search_item returned multiple items {}item={}{}'.format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), id))
                return response[0]
            else:
                self.logger.warning('{}{}{}: search_item returned no results {}item={}{}'.format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), id))
                return None
        except Exception as e:
            self.logger.error("{}{}{}: search_item {}item={}{} {}error={}{}".format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), id, get_tag_ansi_code(), get_log_ansi_code(), e))
            
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
            self.logger.error("{}{}{}: search_all {}search={}{} {}error={}{}".format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), searchString, get_tag_ansi_code(), get_log_ansi_code(), e))
            
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
            self.logger.error("{}{}{}: get_series_id {}series={}{} {}error={}{}".format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), series_name, get_tag_ansi_code(), get_log_ansi_code(), e))
            
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
            self.logger.error("{}{}{}: get_series_episodes {}series={}{} {}error={}{}".format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), series_id, get_tag_ansi_code(), get_log_ansi_code(), e))
    
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
            self.logger.error("{}{}{}: get_movie_item_id {}name={}{} {}error={}{}".format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), name, get_tag_ansi_code(), get_log_ansi_code(), e))

        # return an invalid id if not found
        return self.invalid_item_id
    
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
                self.logger.error('{}{}{}: get_watched_status api response error {}code={}{} {}user={}{} item={}{} {}reason={}{}'.format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), r.status_code, get_tag_ansi_code(), get_log_ansi_code(), user_id, get_tag_ansi_code(), get_log_ansi_code(), item_id, get_tag_ansi_code(), get_log_ansi_code(), r.reason))
                return None
        except Exception as e:
            self.logger.error("{}{}{}: get_watched_status failed for {}user={}{} {}item={}{} {}error={}{}".format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), user_id, get_tag_ansi_code(), get_log_ansi_code(), item_id, get_tag_ansi_code(), get_log_ansi_code(), e))
            
        return False
    
    def set_watched_item(self, user_id, item_id):
        try:
            headers = {'accept': 'application/json'}
            embyUrl = self.get_api_url() + '/Users/' + user_id + '/PlayedItems/' + item_id + '?api_key=' + self.api_key
            requests.post(embyUrl, headers=headers)
        except Exception as e:
            self.logger.error("{}{}{}: set_watched_item {}user={}{} {}item={}{} {}error={}{}".format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), user_id, get_log_ansi_code(), get_tag_ansi_code(), item_id, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), e))
            
    def set_all_library_scan(self):
        try:
            embyRefreshUrl = self.get_api_url() + '/Library/Refresh?api_key=' + self.api_key
            requests.post(embyRefreshUrl)
        except Exception as e:
            self.logger.error("{}{}{}: set_all_library_scan {}error={}{}".format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), e))
    
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
            self.logger.error("{}{}{}: get_library_from_path {}error={}{}".format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), e))
        
        self.logger.warning("{}{}{}: get_library_from_path no library found with {}path={}{}".format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), path))
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
            self.logger.error("{}{}{}: get_library_from_name {}error={}{}".format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), e))
        
        self.logger.warning("{}{}{}: get_library_from_name no library found with {}name={}{}".format(get_emby_ansi_code(), self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), name))
        return ''
