from logging import Logger
from typing import Any
from dataclasses import dataclass, field

from plexapi import server
from plexapi.exceptions import BadRequest, NotFound, Unauthorized

from api.api_base import ApiBase
from common import utils


@dataclass
class PlexCollectionItem:
    """ Individual item in a plex collection """
    title: str
    path: str


@dataclass
class PlexCollection:
    """ Individual collection for plex with items """
    name: str
    items: list[PlexCollectionItem] = field(default_factory=list)


@dataclass
class PlexSearchResult:
    """ Individual search result for plex """
    location: str
    title: str
    library_name: str


@dataclass
class PlexSearchResults:
    """ Search results for plex """
    items: list[PlexSearchResult] = field(default_factory=list)


class PlexAPI(ApiBase):
    """ Represents the api to a plex server """

    def __init__(
        self,
        server_name: str,
        url: str,
        api_key: str,
        media_path: str,
        logger: Logger
    ):
        super().__init__(
            server_name, url, api_key, utils.get_plex_ansi_code(), self.__module__, logger
        )

        self.plex_server = server.PlexServer(url.rstrip("/"), api_key)
        self.media_path = media_path

    def get_server_name(self) -> str:
        """ Name of the plex server """
        return self.server_name

    def get_name(self) -> str:
        """ The name reported by the plex server """
        return self.plex_server.friendlyName

    def get_connection_error_log(self) -> str:
        """ Log for a plex connection error """
        return f"Could not connect to {utils.get_formatted_plex()}:{self.server_name} server {utils.get_tag("url", self.url)} {utils.get_tag("api_key", self.api_key)}"

    def get_media_type_show_name(self) -> str:
        """ The plex name for a show """
        return "show"

    def get_media_type_movie_name(self) -> str:
        """ The plex name for a movie """
        return "movie"

    def get_media_path(self) -> str:
        """ Gets the current media path for the plex server """
        return self.media_path

    def get_invalid_type(self) -> Any:
        """ Returns the invalid type for plex """
        return self.invalid_item_type

    def get_valid(self) -> bool:
        """ Get if the plex server is valid """
        try:
            self.plex_server.library.sections()
            return True
        except (BadRequest, NotFound, Unauthorized):
            pass
        return False

    def get_server_reported_name(self) -> str:
        """
        Retrieves the friendly name of the Plex Media Server.

        Returns:
            str: The friendly name of the Plex server.
        """
        return self.plex_server.friendlyName

    def get_item_path(self, rating_key: Any) -> str:
        """ Retrieves the path of an item in plex """
        try:
            item = self.plex_server.fetchItem(rating_key)
            return item.locations[0]
        except NotFound:
            pass
        return self.get_invalid_type()

    def __search(self, search_str: str, media_type: str) -> PlexSearchResults:
        """ Search the plex server for a string and media type """
        return_results: PlexSearchResults = PlexSearchResults()
        search_results = self.plex_server.search(search_str, media_type)
        for item in search_results:
            return_results.items.append(
                PlexSearchResult(
                    item.locations[0],
                    item.title,
                    item.librarySectionTitle
                )
            )
        return return_results

    def get_library_valid(self, library_name: str) -> bool:
        """ Get if a library is valid """
        try:
            self.plex_server.library.section(library_name)
            return True
        except NotFound:
            pass
        return False

    def set_episode_watched(self, show_name: str, season_num: int, episode_num: int, show_location: str, episode_location: str) -> bool:
        """ Set an episode as watched in plex. Returns if episode was set as watched """
        results = self.__search(
            show_name,
            self.get_media_type_show_name()
        )

        for item in results.items:
            if show_location == item.location:
                try:
                    # Search for the show
                    show = self.plex_server.library.section(
                        item.library_name).get(item.title)
                    if show is not self.get_invalid_type():
                        episode = show.episode(
                            season=season_num, episode=episode_num)
                        if (
                            episode is not None
                            and not episode.isWatched
                            and episode.locations[0] == episode_location
                        ):
                            episode.markWatched()
                            return True
                except NotFound:
                    pass
        return False

    def set_movie_watched(self, movie_name: str, location: str) -> bool:
        """ Set a movie as watched in plex. Returns if movie was set as watched """
        result_items = self.__search(
            movie_name,
            self.get_media_type_movie_name()
        )

        for result_item in result_items.items:
            if location == result_item.location:
                try:
                    library_item = self.plex_server.library.section(
                        result_item.library_name).get(result_item.title)
                    if not library_item.isWatched:
                        library_item.markWatched()
                        return True
                except NotFound:
                    pass
        return False

    def set_library_scan(self, library_name: str) -> None:
        """ Tells plex to scan a library """
        try:
            library = self.plex_server.library.section(library_name)
            library.update()
        except NotFound as e:
            self.logger.error(
                f"{self.log_header} set_library_scan {utils.get_tag("library", library_name)} {utils.get_tag("error", e)}"
            )

    def get_library_name_from_path(self, path: str) -> str:
        """ Returns the name of the plex library from a path """
        # Get all libraries
        libraries = self.plex_server.library.sections()
        for library in libraries:
            for location in library.locations:
                if location == path:
                    return library.title

        self.logger.warning(
            f"{self.log_header} No library found with {utils.get_tag("path", path)}"
        )
        return ""

    def get_collection_valid(
        self,
        library_name: str,
        collection_name: str
    ) -> bool:
        """ Get if a collection is valid """
        try:
            library = self.plex_server.library.section(library_name)
            for collection in library.collections():
                if collection.title == collection_name:
                    return True
        except NotFound:
            pass
        return False

    def get_collection(self, library_name: str, collection_name: str) -> PlexCollection:
        """ Returns a plex collection if valid invalid type if not """
        try:
            library = self.plex_server.library.section(library_name)
            for collection in library.collections():
                if collection.title == collection_name:
                    items: list[PlexCollectionItem] = []
                    for item in collection.children:
                        if len(item.locations) > 0:
                            items.append(
                                PlexCollectionItem(
                                    item.title,
                                    item.locations[0]
                                )
                            )
                    return PlexCollection(collection.title, items)
        except NotFound:
            pass
        return self.get_invalid_type()
