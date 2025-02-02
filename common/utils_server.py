from common.types import MediaServerInfo
from api.plex import PlexAPI
from api.emby import EmbyAPI

def get_connection_info(plex_api: PlexAPI, plex_library: str, emby_api: EmbyAPI, emby_library: str) -> MediaServerInfo:
    plex_valid = plex_library != '' and plex_api.get_valid() and plex_api.get_library(plex_library) != plex_api.get_invalid_type()
    
    emby_valid = False
    emby_library_id = '' 
    if emby_library != '' and emby_api.get_valid() == True:
        library_id = emby_api.get_library_id(emby_library)
        if library_id != emby_api.get_invalid_item_id():
            emby_library_id = library_id
            emby_valid = True
    
    return MediaServerInfo(plex_valid, emby_valid, emby_library_id)
