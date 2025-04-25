""" Utility Server Common Functions """

from common.types import MediaServerInfo
from api.plex import PlexAPI
from api.emby import EmbyAPI


def get_connection_info(
    plex_api: PlexAPI,
    plex_library: str,
    emby_api: EmbyAPI,
    emby_library: str
) -> MediaServerInfo:
    """ Get connection information for Plex and Emby """
    plex_valid: bool = (
        plex_library != ""
        and plex_api.get_valid()
        and plex_api.get_library_valid(plex_library)
    )

    emby_valid: bool = False
    emby_library_id: str = ""
    if emby_library and emby_api.get_valid():
        library_id = emby_api.get_library_id(emby_library)
        if library_id != emby_api.get_invalid_item_id():
            emby_library_id = library_id
            emby_valid = True

    return MediaServerInfo(
        plex_valid,
        emby_valid,
        emby_library_id
    )
