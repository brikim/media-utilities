""" The API to the Tautulli Server """

from logging import Logger
from typing import Any
from dataclasses import dataclass, field

import requests
from requests.exceptions import RequestException

from api.api_base import ApiBase
from common import utils


@dataclass
class TautulliUserInfo:
    """ Class representing an Tautulli User Info """
    id: int
    friendly_name: str


@dataclass
class TautulliHistoryItem:
    """ Class representing an Tautulli History item """
    name: str
    full_name: str
    id: int
    watched: bool
    date_watched: int


@dataclass
class TautulliHistoryItems:
    items: list[TautulliHistoryItem] = field(default_factory=list)


class TautulliAPI(ApiBase):
    """ Represents the api to a Tautulli server """

    def __init__(
        self,
        server_name: str,
        url: str,
        api_key: str,
        logger: Logger
    ):
        super().__init__(
            server_name, url, api_key, utils.get_tautulli_ansi_code(), self.__module__, logger
        )

    def __get_api_url(self) -> str:
        """ URL to use for Tautulli requests """
        return f"{self.url}/api/v2"

    def get_server_name(self) -> str:
        """ Name of the Tautulli server """
        return self.server_name

    def get_connection_error_log(self) -> str:
        """ Log for a Tautulli connection error """
        return f"Could not connect to {utils.get_formatted_tautulli()}({self.server_name}) {utils.get_tag("url", self.url)} {utils.get_tag("api_key", self.api_key)}"

    def get_media_type_episode_name(self) -> str:
        """ The Tautulli name for an episode """
        return "episode"

    def get_media_type_movie_name(self) -> str:
        """ The Tautulli name for a movie """
        return "movie"

    def get_invalid_type(self) -> Any:
        """ Returns the invalid type for Tautulli """
        return self.invalid_item_type

    def __get_payload(self, cmd_name: str) -> dict:
        """ Payload to use for Tautulli requests """
        return {
            "apikey": self.api_key,
            "cmd": cmd_name
        }

    def get_valid(self) -> bool:
        """ Get if the Tautulli server is valid """
        try:
            r = requests.get(self.__get_api_url(), params=self.__get_payload(
                "get_tautulli_info"), timeout=5)
            if r.status_code < 300:
                return True
        except RequestException:
            pass
        return False

    def get_server_reported_name(self) -> str:
        """ Get the name reported by the Tautulli server """
        try:
            r = requests.get(self.__get_api_url(), params=self.__get_payload(
                "get_server_info"), timeout=5)
            return r.json()["response"]["data"]["pms_name"]
        except RequestException as e:
            self.logger.error(
                f"{self.log_header} get_server_info {utils.get_tag("error", e)}"
            )
        return self.get_invalid_type()

    def get_library_id(self, lib_name: str) -> str:
        """ Get the id of a library by name """
        try:
            r = requests.get(self.__get_api_url(), params=self.__get_payload(
                "get_libraries"), timeout=5)
            response = r.json()
            if "response" in response and "data" in response["response"]:
                for lib in response["response"]["data"]:
                    if "section_name" in lib and lib["section_name"] == lib_name and "section_id" in lib:
                        return lib["section_id"]
        except RequestException as e:
            self.logger.error(
                f"{self.log_header} get_library_id {utils.get_tag("library", lib_name)} {utils.get_tag("error", e)}"
            )

        return self.get_invalid_type()

    def get_user_id(self, user_name: str) -> str:
        """ Get the id of a user by name """
        try:
            r = requests.get(
                self.__get_api_url(),
                params=self.__get_payload("get_users"), timeout=5
            )
            response = r.json()

            if "response" in response and "data" in response["response"]:
                for user_data in response["response"]["data"]:
                    if "username" in user_data and user_data["username"] == user_name and "user_id" in user_data:
                        return user_data["user_id"]
        except RequestException as e:
            self.logger.error(
                f"{self.log_header} get_user_id {utils.get_tag("user", user_name)} {utils.get_tag("error", e)}"
            )

        return self.get_invalid_type()

    def get_user_info(self, user_name: str) -> TautulliUserInfo:
        """ Get the info of a user by name """
        try:
            r = requests.get(self.__get_api_url(), params=self.__get_payload(
                "get_users_table"), timeout=5)
            response = r.json()

            if "response" in response and "data" in response["response"] and "data" in response["response"]["data"]:
                for user_info in response["response"]["data"]["data"]:
                    if "username" in user_info and user_info["username"] == user_name:
                        user_id: int = None
                        if "user_id" in user_info:
                            user_id = user_info["user_id"]

                        user_friendly_name: str = ""
                        if "friendly_name" in user_info:
                            user_friendly_name = user_info["friendly_name"]

                        return TautulliUserInfo(user_id, user_friendly_name)
        except RequestException as e:
            self.logger.error(
                f"{self.log_header} get_user_info {utils.get_tag("user", user_name)} {utils.get_tag("error", e)}"
            )

        return self.get_invalid_type()

    def __pack_history_item(self, item: dict) -> TautulliHistoryItem:
        """ Pack a history item into a TautulliHistoryItem """
        item_name: str = ""
        if "title" in item:
            item_name = item["title"]

        item_full_name: str = ""
        if "full_title" in item:
            item_full_name = item["full_title"]

        item_watched: bool = None
        if "watched_status" in item:
            item_watched = item["watched_status"] == 1

        item_id: str = ""
        if "rating_key" in item:
            item_id = item["rating_key"]

        item_watched_date: str = ""
        if "stopped" in item:
            item_watched_date = item["stopped"]

        return TautulliHistoryItem(
            item_name,
            item_full_name,
            item_id,
            item_watched,
            item_watched_date
        )

    def get_watch_history_for_user(self, user_id: int, date_time_for_history: str) -> TautulliHistoryItems:
        """ Get the watch history of a user """
        return_items: TautulliHistoryItems = TautulliHistoryItems()
        try:
            payload = {
                "apikey": self.api_key,
                "cmd": "get_history",
                "include_activity": 0,
                "user_id": user_id,
                "after": date_time_for_history
            }
            r = requests.get(self.__get_api_url(), params=payload, timeout=5)
            response = r.json()

            if "response" in response and "data" in response["response"] and "data" in response["response"]["data"]:
                for item in response["response"]["data"]["data"]:
                    return_items.items.append(
                        self.__pack_history_item(item)
                    )
        except RequestException as e:
            self.logger.error(
                f"{self.log_header} get_watch_history_for_user {utils.get_tag("user_id", user_id)} {utils.get_tag("error", e)}"
            )
        return return_items

    def get_watch_history_for_user_and_library(self, user_id: int, lib_id: str, date_time_for_history: str) -> TautulliHistoryItems:
        """ Get the watch history of a user and library """

        return_items: TautulliHistoryItems = TautulliHistoryItems()
        try:
            payload = {
                "apikey": self.api_key,
                "cmd": "get_history",
                "include_activity": 0,
                "user_id": user_id,
                "section_id": lib_id,
                "after": date_time_for_history
            }
            r = requests.get(self.__get_api_url(), params=payload, timeout=5)
            response = r.json()

            if "response" in response and "data" in response["response"] and "data" in response["response"]["data"]:
                for item in response["response"]["data"]["data"]:
                    return_items.items.append(
                        self.__pack_history_item(item)
                    )

        except RequestException as e:
            self.logger.error(
                f"{self.log_header} get_watch_history_for_user_and_library {utils.get_tag("user_id", user_id)} {utils.get_tag("library_id", lib_id)} {utils.get_tag("error", e)}"
            )

        return return_items

    def get_filename(self, key: int) -> str:
        """ Get the filename of a key """
        try:
            payload = {
                "apikey": self.api_key,
                "rating_key": key,
                "cmd": "get_metadata"
            }
            r = requests.get(self.__get_api_url(), params=payload, timeout=5)
            response = r.json()

            if "response" in response and "data" in response["response"]:
                res_data = response["response"]["data"]
                if (
                    "media_info" in res_data
                    and len(res_data["media_info"]) > 0
                    and "parts" in res_data["media_info"][0]
                    and len(res_data["media_info"][0]["parts"]) > 0
                    and "file" in res_data["media_info"][0]["parts"][0]
                ):
                    return res_data["media_info"][0]["parts"][0]["file"]

        except RequestException as e:
            self.logger.error(
                f"{self.log_header} get_filename {utils.get_tag("key", key)} {utils.get_tag("error", e)}"
            )

        return ""
