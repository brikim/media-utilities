from logging import Logger
from typing import Any
from dataclasses import dataclass, field

import requests

from api.api_base import ApiBase
from common import utils


@dataclass
class EmbyPlaylistItem:
    name: str
    id: str
    playlist_item_id: str


@dataclass
class EmbyPlaylist:
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
        return f"{self.url}/emby"

    def __get_default_header(self) -> dict:
        return {"accept": "application/json"}

    def __get_default_payload(self) -> dict:
        return {"api_key": self.api_key}

    def get_connection_error_log(self) -> str:
        return f"Could not connect to {utils.get_formatted_emby()}:{self.server_name} server {utils.get_tag("url", self.url)} {utils.get_tag("api_key", self.api_key)}"

    def get_media_type_episode_name(self) -> str:
        return "Episode"

    def get_media_type_movie_name(self) -> str:
        return "Movie"

    def get_media_path(self) -> str:
        return self.media_path

    def get_invalid_item_id(self) -> str:
        return self.invalid_item_id

    def get_valid(self) -> bool:
        try:
            r = requests.get(
                f"{self.__get_api_url()}/System/Configuration",
                params=self.__get_default_payload(),
                timeout=5
            )
            if r.status_code < 300:
                return True
        except Exception:
            pass
        return False

    def get_server_reported_name(self) -> str:
        try:
            r = requests.get(
                f"{self.__get_api_url()}/System/Info",
                params=self.__get_default_payload(),
                timeout=5
            )
            response = r.json()
            return response["ServerName"]
        except Exception as e:
            self.logger.error(
                f"{self.log_header} get_name {utils.get_tag("error", e)}"
            )

        return self.get_invalid_item_id()

    def get_user_id(self, userName) -> str:
        try:
            r = requests.get(
                f"{self.__get_api_url()}/Users/Query",
                params=self.__get_default_payload(),
                timeout=5
            )
            response = r.json()

            for item in response["Items"]:
                if item["Name"] == userName:
                    return item["Id"]
        except Exception as e:
            self.logger.error(
                f"{self.log_header} get_user_id {utils.get_tag("user", userName)} {utils.get_tag("error", e)}"
            )

        self.logger.warning(
            f"{self.log_header} get_user_id no user found {utils.get_tag("user", userName)}"
        )
        return self.get_invalid_item_id()

    def search_item(self, id: str) -> Any:
        try:
            payload = {
                "api_key": self.api_key,
                "Ids": id,
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
                return response[0]
            else:
                self.logger.warning(
                    f"{self.log_header} search_item returned no results {utils.get_tag("item", id)}"
                )
        except Exception as e:
            self.logger.error(
                f"{self.log_header} search_item {utils.get_tag("item", id)} {utils.get_tag("error", e)}"
            )

        return None

    def get_item_id_from_path(self, path) -> str:
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

        except Exception as e:
            self.logger.error(
                f"{self.log_header} get_item_id_from_path {utils.get_tag("path", path)} {utils.get_tag("error", e)}"
            )

        return self.get_invalid_item_id()

    def get_watched_status(self, user_id: str, item_id: str) -> bool:
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
        except Exception as e:
            self.logger.error(
                f"{self.log_header} get_watched_status failed for {utils.get_tag("user", user_id)} {utils.get_tag("item", item_id)} {utils.get_tag("error", e)}"
            )

        return None

    def set_watched_item(self, user_id: str, item_id: str):
        try:
            emby_url = f"{self.__get_api_url()}/Users/{user_id}/PlayedItems/{item_id}"
            requests.post(emby_url, headers=self.__get_default_header(
            ), params=self.__get_default_payload(), timeout=5)
        except Exception as e:
            self.logger.error(
                f"{self.log_header} set_watched_item {utils.get_tag("user", user_id)} {utils.get_tag("item", item_id)} {utils.get_tag("error", e)}"
            )

    def set_library_scan(self, library_id: str):
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
        except Exception as e:
            self.logger.error(
                f"{self.log_header} set_library_scan {utils.get_tag("library_id", library_id)} {utils.get_tag("error", e)}"
            )

    def get_library_from_name(self, name: str) -> Any:
        try:
            r = requests.get(
                f"{self.__get_api_url()}/Library/SelectableMediaFolders",
                params=self.__get_default_payload(),
                timeout=5
            )
            response = r.json()

            for library in response:
                if library["Name"] == name:
                    return library
        except Exception as e:
            self.logger.error(
                f"{self.log_header} get_library_from_name {utils.get_tag("name", name)} {utils.get_tag("error", e)}"
            )

        self.logger.warning(
            f"{self.log_header} get_library_from_name no library found with {utils.get_tag("name", name)}"
        )
        return self.get_invalid_item_id()

    def get_library_id(self, name: str) -> Any:
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
        except Exception:
            pass

        return self.get_invalid_item_id()

    def get_playlist_id(self, playlist_name: str) -> str:
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

        except Exception as e:
            self.logger.error(
                f"{self.log_header} get_playlist_id {utils.get_tag("name", playlist_name)} {utils.get_tag("error", e)}"
            )

        return self.get_invalid_item_id()

    def __get_comma_separated_list(self, list_to_separate: list[str]) -> str:
        return ",".join(list_to_separate)

    def create_playlist(
        self,
        playlist_name: str,
        ids: list[str]
    ) -> str:
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
        except Exception as e:
            self.logger.error(
                f"{self.log_header} create_playlist {utils.get_tag("playlist", playlist_name)} {utils.get_tag("error", e)}"
            )
        return self.get_invalid_item_id()

    def get_playlist_items(self, playlist_id: str) -> EmbyPlaylist:
        try:
            playlist = self.search_item(playlist_id)
            if playlist is not None:
                r = requests.get(
                    f"{self.__get_api_url()}/Playlists/{playlist_id}/Items",
                    params=self.__get_default_payload(),
                    timeout=5
                )
                response = r.json()

                emby_playlist = EmbyPlaylist(playlist["Name"], playlist_id)
                for item in response["Items"]:
                    emby_playlist.items.append(
                        EmbyPlaylistItem(
                            item["Name"],
                            item["Id"],
                            item["PlaylistItemId"]
                        )
                    )

                return emby_playlist

        except Exception as e:
            self.logger.error(
                f"{self.log_header} get_playlist_items {utils.get_tag("playlist_id", playlist_id)} {utils.get_tag("error", e)}"
            )

        return None

    def add_playlist_items(self, playlist_id: str, item_ids: list[str]) -> bool:
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
        except Exception as e:
            self.logger.error(
                f"{self.log_header} add_playlist_items {utils.get_tag("playlist_id", playlist_id)} {utils.get_tag("item_ids", item_ids)} {utils.get_tag("error", e)}"
            )
        return False

    def remove_playlist_items(self, playlist_id: str, playlist_item_ids: list[str]) -> bool:
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
        except Exception as e:
            self.logger.error(
                f"{self.log_header} remove_playlist_item {utils.get_tag("playlist_id", playlist_id)} {utils.get_tag("playlist_item_ids", playlist_item_ids)} {utils.get_tag("error", e)}"
            )
        return False

    def set_move_playlist_item_to_index(self, playlist_id: str, playlist_item_id: str, index: int) -> bool:
        try:
            emby_url = f"{self.__get_api_url()}/Playlists/{playlist_id}/Items/{playlist_item_id}/Move/{str(index)}"
            r = requests.post(emby_url, headers=self.__get_default_header(
            ), params=self.__get_default_payload(), timeout=5)
            if r.status_code < 300:
                return True
        except Exception as e:
            self.logger.error(
                f"{self.log_header} set_move_playlist_item_to_index {utils.get_tag("playlist_id", playlist_id)} {utils.get_tag("playlist_item_id", playlist_item_id)} {utils.get_tag("move_index", index)} {utils.get_tag("error", e)}"
            )
        return False
