import requests
import json
from common.utils import remove_year_from_name
class EmbyAPI:
    def __init__(self, url, api_key, logger):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.logger = logger
        self.invalid_item_id = '0'
    
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
            'IncludeItemTypes': mediaType}
            
            r = requests.get(self.get_api_url() + '/Items', params=payload)
            response = r.json()
            
            return response['Items']
        except Exception as e:
            self.logger.error("{}: Get Emby Search {} ERROR:{}".format(self.__module__, searchString, e))
    
    def search_all(self, searchString):
        try:
            payload = {
            'api_key': self.api_key,
            'Recursive': 'true',
            'SearchTerm': searchString}
            
            r = requests.get(self.get_api_url() + '/Items', params=payload)
            return r.json()['Items']
        except Exception as e:
            self.logger.error("{}: Get Emby Search {} ERROR:{}".format(self.__module__, searchString, e))
            
    def get_series_id(self, series_name):
        # Remove any year from the series name ... example (2017)
        cleaned_series_name = remove_year_from_name(series_name)
        cleaned_series_name = cleaned_series_name.lower()

        try:
            search_items = self.search(cleaned_series_name, 'Series')
            for item in search_items:
                lower_series_name = item['Name'].lower()
                if (lower_series_name.find(cleaned_series_name) >= 0 or series_name.lower().find(lower_series_name) >= 0):
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
            'Season': season_num}
            
            r = requests.get(self.get_api_url() + '/Shows/' + series_id + '/Episodes' , params=payload)
            return r.json()['Items']
        except Exception as e:
            self.logger.error("{}: Get Emby Series Episodes {} ERROR:{}".format(self.__module__, series_id, e))
    
    def get_series_episode_id(self, series_name, season_num, episode_num):
        series_id = self.get_series_id(series_name)
        if series_id != self.invalid_item_id:
            series_episodes = self.get_series_episodes(series_id, season_num)
            for episode in series_episodes:
                if episode['ParentIndexNumber'] == season_num and episode['IndexNumber'] == episode_num:
                    return episode['Id']
        
        return self.invalid_item_id
    
    def get_movie_item_id(self, name):
        try:
            searchItems = self.search(name, 'Movie')
            for item in searchItems:
                if item['Name'].lower() == name.lower():
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
            
    def set_library_refresh(self):
        try:
            embyRefreshUrl = self.get_api_url() + '/Library/Refresh?api_key=' + self.api_key
            requests.post(embyRefreshUrl)
        except Exception as e:
            self.logger.error("{}: Set Emby library refresh ERROR:{}".format(self.__module__, e))
