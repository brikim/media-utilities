""" The API to the Emby Media Server """

from logging import Logger
from dataclasses import dataclass, field

import requests
from requests.exceptions import RequestException

from api.api_base import ApiBase
from common import utils


@dataclass
class EmbyItem:
    """ Class representing an emby item """
    name: str
    id: str
    path: str
    type: str
    series_name: str
    season_num: int
    episode_num: int


@dataclass
class EmbyPlaylistItem:
    """ Class representing an emby playlist item """
    name: str
    id: str
    playlist_item_id: str


@dataclass
class EmbyPlaylist:
    """ Class representing an emby playlist """
    name: str
    id: str
    items: list[EmbyPlaylistItem] = field(default_factory=list)


class EmbyAPI(ApiBase):
    """
    Provides an interface for interacting with the Emby Media Server API.

    This class extends ApiBase and provides methods for checking server
    validity, retrieving server name, checking library existence, and
    triggering library scans.
    """

    def __init__(
        self,
        server_name: str,
        url: str,
        api_key: str,
        media_path: str,
        logger: Logger
    ):
        """
        Initializes the EmbyAPI with the server URL, API key, and logger.

        Args:
            server_name (str): The name of this emby server
            url (str): The base URL of the Emby Media Server.
            api_key (str): The API key for authenticating with the Emby server.
            logger (Logger): The logger instance for logging messages.
        """
        super().__init__(
            server_name, url, api_key, utils.get_emby_ansi_code(), self.__module__, logger
        )

        self.media_path = media_path

    def __get_api_url(self) -> str:
        """ URL to use for emby requests """
        return f"{self.url}/emby"

    def __get_default_header(self) -> dict:
        """ Default header to use in emby requests """
        return {"accept": "application/json"}

    def __get_default_payload(self) -> dict:
        """ Default payload to use in emby requests """
        return {"api_key": self.api_key}

    def get_connection_error_log(self) -> str:
        """ Log for a emby connection error """
        return f"Could not connect to {utils.get_formatted_emby()}:{self.server_name} server {utils.get_tag("url", self.url)} {utils.get_tag("api_key", self.api_key)}"

    def get_media_type_episode_name(self) -> str:
        """ The emby name for an episode """
        return "Episode"

    def get_media_type_movie_name(self) -> str:
        """ The emby name for a movie """
        return "Movie"

    def get_media_path(self) -> str:
        """ Gets the current media path for the emby server """
        return self.media_path

    def get_invalid_item_id(self) -> str:
        """ Returns the invalid item id for emby """
        return self.invalid_item_id

    def get_valid(self) -> bool:
        """ Get if the emby server is valid """
        try:
            r = requests.get(
                f"{self.__get_api_url()}/System/Configuration",
                params=self.__get_default_payload(),
                timeout=5
            )
            if r.status_code < 300:
                return True
        except RequestException:
            pass
        return False

    def get_server_reported_name(self) -> str:
        """ Get the name reported by the emby server """
        try:
            r = requests.get(
                f"{self.__get_api_url()}/System/Info",
                params=self.__get_default_payload(),
                timeout=5
            )
            response = r.json()
            return response["ServerName"]
        except RequestException as e:
            self.logger.error(
                f"{self.log_header} get_name {utils.get_tag("error", e)}"
            )

        return self.get_invalid_item_id()

    def get_user_id(self, user_name: str) -> str:
        """ Get the id of a user by name """
        try:
            r = requests.get(
                f"{self.__get_api_url()}/Users/Query",
                params=self.__get_default_payload(),
                timeout=5
            )
            response = r.json()

            for item in response["Items"]:
                if item["Name"] == user_name:
                    return item["Id"]
        except RequestException as e:
            self.logger.error(
                f"{self.log_header} get_user_id {utils.get_tag("user", user_name)} {utils.get_tag("error", e)}"
            )

        self.logger.warning(
            f"{self.log_header} get_user_id no user found {utils.get_tag("user", user_name)}"
        )
        return self.get_invalid_item_id()

    def search_item(self, emby_id: str) -> EmbyItem:
        """ Search for an item by id """
        try:
            payload = {
                "api_key": self.api_key,
                "Ids": emby_id,
                "Fields": "Path"
            }
            r = requests.get(
                f"{self.__get_api_url()}/Items",
                params=payload,
                timeout=5
            )
            response = r.json()["Items"]
            response_length = len(response)
            if response_length > 0:
                if (response_length > 1):
                    self.logger.warning(
                        f"{self.log_header} search_item returned multiple items {utils.get_tag("item", id)}"
                    )

                main_response = response[0]

                item_type: str = None
                if "Type" in main_response:
                    item_type = main_response["Type"]

                item_name: str = None
                if "Name" in main_response:
                    item_name = main_response["Name"]

                item_path: str = None
                if "Path" in main_response:
                    item_path = main_response["Path"]

                item_series_name: str = None
                if "SeriesName" in main_response:
                    item_series_name = main_response["SeriesName"]

                item_season_num: int = None
                if "ParentIndexNumber" in main_response:
                    item_season_num = main_response["ParentIndexNumber"]

                item_episode_num: int = None
                if "IndexNumber" in main_response:
                    item_episode_num = main_response["IndexNumber"]

                return EmbyItem(item_name, emby_id, item_path, item_type, item_series_name, item_season_num, item_episode_num)
            else:
                self.logger.warning(
                    f"{self.log_header} search_item returned no results {utils.get_tag("item", id)}"
                )
        except RequestException as e:
            self.logger.error(
                f"{self.log_header} search_item {utils.get_tag("item", id)} {utils.get_tag("error", e)}"
            )

        return None

    def get_item_id_from_path(self, path) -> str:
        """ Get the id of an item by path """
        try:
            payload = {
                "api_key": self.api_key,
                "Recursive": "true",
                "Path": path,
                "Fields": "Path"
            }
            r = requests.get(
                f"{self.__get_api_url()}/Items",
                params=payload,
                timeout=5
            )
            response = r.json()

            if response["TotalRecordCount"] > 0:
                return response["Items"][0]["Id"]

        except RequestException as e:
            self.logger.error(
                f"{self.log_header} get_item_id_from_path {utils.get_tag("path", path)} {utils.get_tag("error", e)}"
            )

        return self.get_invalid_item_id()

    def get_watched_status(self, user_id: str, item_id: str) -> bool:
        """ Get the watched status of an item """
        try:
            payload = {
                "api_key": self.api_key,
                "Ids": item_id,
                "IsPlayed": "true"
            }
            r = requests.get(
                f"{self.__get_api_url()}/Users/{user_id}/Items",
                params=payload,
                timeout=5
            )
            if r.status_code < 300:
                return r.json()["TotalRecordCount"] > 0
            else:
                self.logger.error(
                    f"{self.log_header} get_watched_status api response error {utils.get_tag("code", r.status_code)} {utils.get_tag("user", user_id)} {utils.get_tag("item", item_id)} {utils.get_tag("error", r.reason)}"
                )
        except RequestException as e:
            self.logger.error(
                f"{self.log_header} get_watched_status failed for {utils.get_tag("user", user_id)} {utils.get_tag("item", item_id)} {utils.get_tag("error", e)}"
            )

        return None

    def set_watched_item(self, user_id: str, item_id: str) -> None:
        """ Set an item as watched """
        try:
            emby_url = f"{self.__get_api_url()}/Users/{user_id}/PlayedItems/{item_id}"
            requests.post(
                emby_url, headers=self.__get_default_header(),
                params=self.__get_default_payload(), timeout=5)
        except RequestException as e:
            self.logger.error(
                f"{self.log_header} set_watched_item {utils.get_tag("user", user_id)} {utils.get_tag("item", item_id)} {utils.get_tag("error", e)}"
            )

    def set_library_scan(self, library_id: str) -> None:
        """ Tells emby to scan a library """
        try:
            payload = {
                "api_key": self.api_key,
                "Recursive": "true",
                "ImageRefreshMode": "Default",
                "MetadataRefreshMode": "Default",
                "ReplaceAllImages": "false",
                "ReplaceAllMetadata": "false",
            }
            emby_url = f"{self.__get_api_url()}/Items/{library_id}/Refresh"
            requests.post(
                emby_url, headers=self.__get_default_header(), params=payload, timeout=5)
        except RequestException as e:
            self.logger.error(
                f"{self.log_header} set_library_scan {utils.get_tag("library_id", library_id)} {utils.get_tag("error", e)}"
            )

    def get_library_valid(self, name: str) -> bool:
        """ Get the validity of a library by name """
        try:
            r = requests.get(
                f"{self.__get_api_url()}/Library/SelectableMediaFolders",
                params=self.__get_default_payload(),
                timeout=5
            )
            response = r.json()

            for library in response:
                if library["Name"] == name:
                    return True
        except RequestException as e:
            self.logger.error(
                f"{self.log_header} get_library_from_name {utils.get_tag("name", name)} {utils.get_tag("error", e)}"
            )

        self.logger.warning(
            f"{self.log_header} get_library_from_name no library found with {utils.get_tag("name", name)}"
        )
        return False

    def get_library_id(self, name: str) -> str:
        """ Get a library id by name """
        try:
            r = requests.get(
                f"{self.__get_api_url()}/Library/SelectableMediaFolders",
                params=self.__get_default_payload(),
                timeout=5
            )
            response = r.json()

            for library in response:
                if library["Name"] == name:
                    return library["Id"]
        except RequestException:
            pass

        return self.get_invalid_item_id()

    def get_playlist_id(self, playlist_name: str) -> str:
        """ Get a playlist id by name """
        try:
            payload = {
                "api_key": self.api_key,
                "SearchTerm": playlist_name,
                "Recursive": "true",
                "Fields": "Path",
            }
            r = requests.get(
                f"{self.__get_api_url()}/Items",
                params=payload,
                timeout=5
            )
            response = r.json()

            for item in response["Items"]:
                if item["Type"] == "Playlist" and item["Name"] == playlist_name:
                    return item["Id"]

        except RequestException as e:
            self.logger.error(
                f"{self.log_header} get_playlist_id {utils.get_tag("name", playlist_name)} {utils.get_tag("error", e)}"
            )

        return self.get_invalid_item_id()

    def __get_comma_separated_list(self, list_to_separate: list[str]) -> str:
        """ Get a comma separated string from a list """
        return ",".join(list_to_separate)

    def create_playlist(
        self,
        playlist_name: str,
        ids: list[str]
    ) -> str:
        """ Create a playlist """
        try:
            payload = {
                "api_key": self.api_key,
                "Name": playlist_name,
                "Ids": self.__get_comma_separated_list(ids),
                "MediaType": "Movies",
            }
            emby_url = f"{self.__get_api_url()}/Playlists"
            r = requests.post(
                emby_url, headers=self.__get_default_header(), params=payload, timeout=5)
            if r.status_code < 300:
                response = r.json()
                return response["Id"]
        except RequestException as e:
            self.logger.error(
                f"{self.log_header} create_playlist {utils.get_tag("playlist", playlist_name)} {utils.get_tag("error", e)}"
            )
        return self.get_invalid_item_id()

    def get_playlist_items(self, playlist_id: str) -> EmbyPlaylist:
        """ Get the items in a playlist """
        try:
            playlist = self.search_item(playlist_id)
            if playlist is not None:
                r = requests.get(
                    f"{self.__get_api_url()}/Playlists/{playlist.id}/Items",
                    params=self.__get_default_payload(),
                    timeout=5
                )
                response = r.json()

                emby_playlist = EmbyPlaylist(playlist.name, playlist.id)
                for item in response["Items"]:
                    emby_playlist.items.append(
                        EmbyPlaylistItem(
                            item["Name"],
                            item["Id"],
                            item["PlaylistItemId"]
                        )
                    )

                return emby_playlist

        except RequestException as e:
            self.logger.error(
                f"{self.log_header} get_playlist_items {utils.get_tag("playlist_id", playlist_id)} {utils.get_tag("error", e)}"
            )

        return None

    def add_playlist_items(self, playlist_id: str, item_ids: list[str]) -> bool:
        """ Add items to a playlist """
        try:
            payload = {
                "api_key": self.api_key,
                "Ids": self.__get_comma_separated_list(item_ids),
            }
            emby_url = f"{self.__get_api_url()}/Playlists/{playlist_id}/Items"
            r = requests.post(
                emby_url, headers=self.__get_default_header(), params=payload, timeout=5)
            if r.status_code < 300:
                return True
        except RequestException as e:
            self.logger.error(
                f"{self.log_header} add_playlist_items {utils.get_tag("playlist_id", playlist_id)} {utils.get_tag("item_ids", item_ids)} {utils.get_tag("error", e)}"
            )
        return False

    def remove_playlist_items(self, playlist_id: str, playlist_item_ids: list[str]) -> bool:
        """ Remove items from a playlist """
        try:
            payload = {
                "api_key": self.api_key,
                "EntryIds": self.__get_comma_separated_list(playlist_item_ids),
            }
            emby_url = f"{self.__get_api_url()}/Playlists/{playlist_id}/Items/Delete"
            r = requests.post(
                emby_url, headers=self.__get_default_header(), params=payload, timeout=5)
            if r.status_code < 300:
                return True
        except RequestException as e:
            self.logger.error(
                f"{self.log_header} remove_playlist_item {utils.get_tag("playlist_id", playlist_id)} {utils.get_tag("playlist_item_ids", playlist_item_ids)} {utils.get_tag("error", e)}"
            )
        return False

    def set_move_playlist_item_to_index(self, playlist_id: str, playlist_item_id: str, index: int) -> bool:
        """ Move a playlist item to a new index """
        try:
            emby_url = f"{self.__get_api_url()}/Playlists/{playlist_id}/Items/{playlist_item_id}/Move/{str(index)}"
            r = requests.post(emby_url, headers=self.__get_default_header(
            ), params=self.__get_default_payload(), timeout=5)
            if r.status_code < 300:
                return True
        except RequestException as e:
            self.logger.error(
                f"{self.log_header} set_move_playlist_item_to_index {utils.get_tag("playlist_id", playlist_id)} {utils.get_tag("playlist_item_id", playlist_item_id)} {utils.get_tag("move_index", index)} {utils.get_tag("error", e)}"
            )
        return False
