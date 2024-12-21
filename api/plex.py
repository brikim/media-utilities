import requests
import json
from plexapi.server import PlexServer

class PlexAPI:
    def __init__(self, url, api_key, admin_user_name, logger):
        self.plex_server = PlexServer(url.rstrip('/'), api_key)
        self.admin_user_name = admin_user_name
        self.logger = logger
        self.item_invalid_type = None
        
    def get_invalid_type(self):
        return self.item_invalid_type
    
    def switch_plex_account(self, user_name):
        try:
            current_user = self.plex_server.myPlexAccount()
            if current_user.username != user_name:
                self.plex_server.switchUser(user_name)
        except Exception as e:
            self.logger.error('{}: Failed to switch plex account to user {} Error:{}'.format(self.__module__, user_name, e))
    
    def switch_plex_account_admin(self):
        self.switch_plex_account(self.admin_user_name)
        
    def fetchItem(self, rating_key):
        returnItem = None
        try:
            returnItem = self.plex_server.fetchItem(rating_key)
        except Exception as e:
            pass
        return returnItem
    
    def search(self, searchStr, media_type):
        return self.plex_server.search(searchStr, media_type)
    
    def get_library_item(self, library_name, title):
        return_show = None
        try:
            return_show = self.plex_server.library.section(library_name).get(title)
        except Exception as e:
            pass
        return return_show
    
    def set_library_refresh(self, library_name):
        try:
            library = self.plex_server.library.section(library_name)
            library.refresh()
        except Exception as e:
            self.logger.error('{}: Failed to refresh Plex library {} Error: {}'.format(self.__module__, library_name, e))