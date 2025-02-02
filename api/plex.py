from logging import Logger
from typing import Any
from plexapi.server import PlexServer
from common.utils import get_plex_ansi_code, get_log_header, get_tag, get_formatted_plex

class PlexAPI:
    def __init__(self, url: str, api_key: str, admin_user_name: str, media_path: str, logger: Logger):
        self.url = url
        self.api_key = api_key
        self.plex_server = PlexServer(url.rstrip('/'), api_key)
        self.admin_user_name = admin_user_name
        self.media_path = media_path
        self.logger = logger
        self.item_invalid_type = None
        self.log_header = get_log_header(get_plex_ansi_code(), self.__module__)
        
    def get_valid(self) -> bool:
        try:
            self.plex_server.library.sections()
            return True
        except Exception as e:
            pass
        return False
    
    def get_connection_error_log(self) -> str:
        return 'Could not connect to {} server {} {}'.format(get_formatted_plex(), get_tag('url', self.url), get_tag('api_key', self.api_key))
    
    def get_media_type_show_name(self) -> str:
        return 'show'
    
    def get_media_type_movie_name(self) -> str:
        return 'movie'
    
    def get_media_path(self) -> str:
        return self.media_path
    
    def get_invalid_type(self) -> Any:
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
        
    def fetchItem(self, rating_key: Any) -> Any:
        returnItem = self.get_invalid_type()
        try:
            returnItem = self.plex_server.fetchItem(rating_key)
        except Exception as e:
            pass
        return returnItem
    
    def search(self, searchStr: str, media_type: str) -> Any:
        return self.plex_server.search(searchStr, media_type)
    
    def get_library(self, library_name: str) -> Any:
        try:
            return self.plex_server.library.section(library_name)
        except Exception as e:
            pass
        return self.get_invalid_type()
        
    def get_library_item(self, library_name: str, title: str) -> Any:
        try:
            return self.plex_server.library.section(library_name).get(title)
        except Exception as e:
            pass
        return self.get_invalid_type()
    
    def set_library_scan(self, library_name: str):
        try:
            library = self.plex_server.library.section(library_name)
            library.update()
        except Exception as e:
            self.logger.error("{} set_library_scan {} {}".format(self.log_header, get_tag('library', library_name), get_tag('error', e)))
            
    def get_library_name_from_path(self, path: str) -> str:
        # Get all libraries
        libraries = self.plex_server.library.sections()
        for library in libraries:
            for location in library.locations:
                if location == path:
                    return library.title
        
        self.logger.warning("{} No library found with {}".format(self.log_header, get_tag('path', path)))
        return ''