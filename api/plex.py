from logging import Logger
from typing import Any
from plexapi import server, collection
from common import utils
from dataclasses import dataclass, field

@dataclass
class PlexCollectionItem:
    title: str
    path: str
    
@dataclass
class PlexCollection:
    name: str
    items: list[PlexCollectionItem] = field(default_factory=list)
    
class PlexAPI:
    def __init__(self, url: str, api_key: str, admin_user_name: str, media_path: str, logger: Logger):
        self.url = url
        self.api_key = api_key
        self.plex_server = server.PlexServer(url.rstrip('/'), api_key)
        self.admin_user_name = admin_user_name
        self.media_path = media_path
        self.logger = logger
        self.item_invalid_type = None
        self.log_header = utils.get_log_header(utils.get_plex_ansi_code(), self.__module__)
        
    def get_valid(self) -> bool:
        try:
            self.plex_server.library.sections()
            return True
        except Exception as e:
            pass
        return False
    
    def get_name(self) -> str:
        return self.plex_server.friendlyName
    
    def get_connection_error_log(self) -> str:
        return 'Could not connect to {} server {} {}'.format(utils.get_formatted_plex(),  utils.get_tag('url', self.url),  utils.get_tag('api_key', self.api_key))
    
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
            self.logger.error('{} switch_plex_account {} {}'.format(self.log_header,  utils.get_tag('user', user_name),  utils.get_tag('error', e)))
    
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
            self.logger.error('{} set_library_scan {} {}'.format(self.log_header,  utils.get_tag('library', library_name),  utils.get_tag('error', e)))
            
    def get_library_name_from_path(self, path: str) -> str:
        # Get all libraries
        libraries = self.plex_server.library.sections()
        for library in libraries:
            for location in library.locations:
                if location == path:
                    return library.title
        
        self.logger.warning('{} No library found with {}'.format(self.log_header,  utils.get_tag('path', path)))
        return ''
    
    def get_collection_valid(self, library_name: str, collection_name: str) -> bool:
        try:
            library = self.plex_server.library.section(library_name)
            for collection in library.collections():
                if collection.title == collection_name:
                    return True
        except Exception as e:
            pass
        return False
    
    def get_collection(self, library_name: str, collection_name: str) -> PlexCollection:
        try:
            library = self.plex_server.library.section(library_name)
            for collection in library.collections():
                if collection.title == collection_name:
                    items: list[PlexCollectionItem] = []
                    for item in collection.children:
                        if len(item.locations) > 0:
                            items.append(PlexCollectionItem(item.title, item.locations[0]))
                    return PlexCollection(collection.title, items)
        except Exception as e:
            pass
        return self.get_invalid_type()
