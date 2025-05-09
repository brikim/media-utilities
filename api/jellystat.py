""" The API to the Jellystat Server """

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import requests
from requests.exceptions import RequestException

from api.api_base import ApiBase
from common import utils
from common.log_manager import LogManager


@dataclass
class JellystatHistoryItem:
    """ Class representing an Jellystat History item """
    name: str
    id: str
    user_name: str
    date_watched: str
    date_time: datetime
    series_name: str
    episode_id: str


@dataclass
class JellystatHistoryItems:
    """ Class representing an Jellystat History items """
    items: list[JellystatHistoryItem] = field(default_factory=list)


class JellystatAPI(ApiBase):
    """ Represents the api to a jellystat server """

    def __init__(
        self,
        server_name: str,
        url: str,
        api_key: str,
        log_manager: LogManager
    ):
        super().__init__(
            server_name,
            url,
            api_key,
            utils.get_jellystat_ansi_code(),
            self.__module__,
            log_manager
        )

    def get_connection_error_log(self) -> str:
        """ Log for a jellystat connection error """
        return (
            f"Could not connect to {utils.get_formatted_jellystat()}:{self.server_name} "
            f"{utils.get_tag("url", self.url)} "
            f"{utils.get_tag("api_key", self.api_key)}"
        )

    def get_invalid_type(self) -> Any:
        """ Returns the invalid type for jellystat """
        return self.invalid_item_type

    def get_api_url(self) -> str:
        """ URL to use for jellystat requests """
        return f"{self.url}/api"

    def get_headers(self) -> dict:
        """ Headers to use for jellystat requests """
        return {"x-api-token": self.api_key,
                "Content-Type": "application/json"}

    def get_valid(self) -> bool:
        """ Get if the jellystat server is valid """
        try:
            payload = {}
            r = requests.get(
                f"{self.get_api_url()}/getconfig",
                headers=self.get_headers(),
                params=payload,
                timeout=5
            )
            if r.status_code < 300:
                return True
        except RequestException:
            pass
        return False

    def get_library_id(self, lib_name: str) -> str:
        """ Get the id of a library by name """
        try:
            payload = {}
            r = requests.get(
                f"{self.get_api_url()}/getLibraries",
                headers=self.get_headers(),
                params=payload,
                timeout=5
            )
            response = r.json()
            for lib in response:
                if "Name" in lib and lib["Name"] == lib_name and "Id" in lib and lib["Id"]:
                    return lib["Id"]
        except RequestException as e:
            self.log_manager.log_error(
                f"{self.log_header} get_library_id "
                f"{utils.get_tag("library_name", lib_name)} "
                f"{utils.get_tag("error", e)}"
            )

        return self.get_invalid_type()

    def __get_history_item(self, item: dict) -> JellystatHistoryItem:
        """ Get a history item from a dictionary """
        item_name: str = ""
        if "NowPlayingItemName" in item:
            item_name = item["NowPlayingItemName"]

        item_id: str = ""
        if "NowPlayingItemId" in item:
            item_id = item["NowPlayingItemId"]

        item_user_name: str = ""
        if "UserName" in item:
            item_user_name = item["UserName"]

        item_activity_date: str = ""
        item_date_time: datetime = None
        if "ActivityDateInserted" in item:
            item_activity_date = item["ActivityDateInserted"]
            item_date_time = datetime.fromisoformat(item_activity_date)
        else:
            item_date_time = datetime.now()
            self.log_manager.log_warning(
                f"{self.log_header} __get_history_item "
                f"no ActivityDateInserted for item {item_name}"
            )

        item_series_name: str = ""
        if "SeriesName" in item:
            item_series_name = item["SeriesName"]

        item_episode_id: str = ""
        if "EpisodeId" in item:
            item_episode_id = item["EpisodeId"]

        return JellystatHistoryItem(
            item_name,
            item_id,
            item_user_name,
            item_activity_date,
            item_date_time,
            item_series_name,
            item_episode_id
        )

    def get_user_watch_history(self, user_id: str) -> JellystatHistoryItems:
        """ Get the watch history of a user """
        try:
            payload = {
                "userid": user_id
            }
            r = requests.post(
                f"{self.get_api_url()}/getUserHistory",
                headers=self.get_headers(),
                data=json.dumps(payload),
                timeout=5
            )

            response = r.json()
            if "results" in response:
                jellystat_history_items: JellystatHistoryItems = JellystatHistoryItems()
                for item in response["results"]:
                    jellystat_history_items.items.append(
                        self.__get_history_item(item)
                    )

                return jellystat_history_items
            else:
                return response
        except RequestException as e:
            self.log_manager.log_error(
                f"{self.log_header} get_user_watch_history "
                f"{utils.get_tag("user_id", user_id)} "
                f"{utils.get_tag("error", e)}"
            )

        return self.get_invalid_type()

    def get_library_history(self, library_id: str) -> JellystatHistoryItems:
        """ Get the watch history of a library """
        try:
            payload = {
                "libraryid": library_id
            }
            r = requests.post(
                f"{self.get_api_url()}/getLibraryHistory",
                headers=self.get_headers(),
                data=json.dumps(payload),
                timeout=5
            )

            response = r.json()

            jellystat_history_items: JellystatHistoryItems = JellystatHistoryItems()
            if "results" in response:
                for item in response["results"]:
                    jellystat_history_items.items.append(
                        self.__get_history_item(item)
                    )
            else:
                jellystat_history_items.items.append(
                    self.__get_history_item(response)
                )

            return jellystat_history_items
        except RequestException as e:
            self.log_manager.log_error(
                f"{self.log_header} get_library_history "
                f"{utils.get_tag("lib_id", library_id)} "
                f"{utils.get_tag("error", e)}"
            )

        return self.get_invalid_type()
