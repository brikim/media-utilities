import requests
import json
from plexapi.server import PlexServer
from common.utils import get_plex_ansi_code, get_log_header, get_tag

class PlexAPI:
    def __init__(self, url, api_key, admin_user_name, media_path, logger):
        self.plex_server = PlexServer(url.rstrip('/'), api_key)
        self.admin_user_name = admin_user_name
        self.media_path = media_path
        self.logger = logger
        self.item_invalid_type = None
        self.valid = False
        self.log_header = get_log_header(get_plex_ansi_code(), self.__module__)
        
        try:
            self.plex_server.library.sections()
            self.valid = True
        except Exception as e:
            self.logger.warning('{} could not connect to service'.format(self.log_header))
            self.valid = False
        
    def get_valid(self):
        return self.valid
    
    def get_media_type_show_name(self):
        return 'show'
    
    def get_media_type_movie_name(self):
        return 'movie'
    
    def get_media_path(self):
        return self.media_path
    
    def get_invalid_type(self):
        return self.item_invalid_type
    
    def switch_plex_account(self, user_name):
        try:
            current_user = self.plex_server.myPlexAccount()
            if current_user.username != user_name:
                self.plex_server.switchUser(user_name)
        except Exception as e:
            self.logger.error("{} switch_plex_account {} {}".format(self.log_header, get_tag('user', user_name), get_tag('error', e)))
    
    def switch_plex_account_admin(self):
        self.switch_plex_account(self.admin_user_name)
        
    def fetchItem(self, rating_key):
        returnItem = self.get_invalid_type()
        try:
            returnItem = self.plex_server.fetchItem(rating_key)
        except Exception as e:
            pass
        return returnItem
    
    def search(self, searchStr, media_type):
        return self.plex_server.search(searchStr, media_type)
    
    def get_library(self, library_name):
        try:
            return self.plex_server.library.section(library_name)
        except Exception as e:
            pass
        return self.get_invalid_type()
        
    def get_library_item(self, library_name, title):
        return_show = self.get_invalid_type()
        try:
            return_show = self.plex_server.library.section(library_name).get(title)
        except Exception as e:
            pass
        return return_show
    
    def set_library_scan(self, library_name):
        try:
            library = self.plex_server.library.section(library_name)
            library.update()
        except Exception as e:
            self.logger.error("{} set_library_scan {} {}".format(self.log_header, get_tag('library', library_name), get_tag('error', e)))
            
    def get_library_name_from_path(self, path):
        # Get all libraries
        libraries = self.plex_server.library.sections()
        for library in libraries:
            for location in library.locations:
                if location == path:
                    return library.title
        
        self.logger.warning("{} No library found with {}".format(self.log_header, get_tag('path', path)))
        return ''