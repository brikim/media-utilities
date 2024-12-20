import requests
import json

class EmbyServer:
    def __init__(self, url, api_key, logger):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.logger = logger

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

        return '0'
    
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
            
    def get_episode_item_id(self, seriesName, episodeName):
        # Remove any year from the series name ... example (2017)
        cleanedSeriesName = seriesName
        openIndex = seriesName.find(" (")
        if openIndex >= 0:
            closeIndex = seriesName.find(")")
            if closeIndex > openIndex:
                cleanedSeriesName = seriesName[0:openIndex] + seriesName[closeIndex+1:len(cleanedSeriesName)]
        cleanedSeriesName = cleanedSeriesName.lower()

        try:
            searchItems = self.search(cleanedSeriesName + ' ' + episodeName, 'Episode')
            for item in searchItems:
                lowerItemSeriesName = item['SeriesName'].lower()
                if (lowerItemSeriesName == cleanedSeriesName or lowerItemSeriesName == seriesName.lower()) and (item['Name'].lower() == episodeName.lower()):
                    return item['Id']
        except Exception as e:
            self.logger.error("{}: Get Emby Episode Items({}) ERROR:{}".format(self.__module__, seriesName + ' ' + episodeName, e))
            
        # return an invalid id if not found
        return '0'
    
    def get_movie_item_id(self, name):
        try:
            searchItems = self.search(name, 'Movie')
            for item in searchItems:
                if item['Name'].lower() == name.lower():
                    return item['Id']
        except Exception as e:
            self.logger.error("{}: Get Emby Movie Items({}) ERROR:{}".format(self.__module__, name, e))

        # return an invalid id if not found
        return '0'
    
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
