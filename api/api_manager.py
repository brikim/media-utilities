""" Api Manager """

from datetime import datetime
import time

from common import utils
from common.log_manager import LogManager

from api.api_base import ApiBase
from api.emby import EmbyAPI
from api.jellystat import JellystatAPI
from api.plex import PlexAPI
from api.tautulli import TautulliAPI


class ApiManager:
    """
    Manages the API connections to different media servers (Plex, Emby, Tautulli and Jellystat).
    """

    def __init__(
        self,
        config: dict,
        log_manager: LogManager
    ):
        """
        Initializes the ApiManager and establishes connections to configured media servers.
        """
        self.plex_api_list: list[PlexAPI] = []
        self.tautulli_api_list: list[TautulliAPI] = []
        self.emby_api_list: list[EmbyAPI] = []
        self.jellystat_api_list: list[JellystatAPI] = []
        self.log_manager = log_manager

        if "plex" in config and "servers" in config["plex"]:
            for server in config["plex"]["servers"]:
                self.__create_plex_server(server)

        if "emby" in config and "servers" in config["emby"]:
            for server in config["emby"]["servers"]:
                self.__create_emby_server(server)

    def __wait_api_valid(
        self,
        api: ApiBase,
        formatted_name: str
    ) -> bool:
        start_time: datetime = datetime.now()
        current_time: datetime = start_time
        while (current_time - start_time).total_seconds() < 10:
            if api.get_valid():
                server_name = (
                    api.get_server_reported_name()
                    if api.get_server_reported_name()
                    else api.get_server_name()
                )
                self.log_manager.log_info(
                    f"Connected to {formatted_name}({server_name}) successfully"
                )
                return True

            # Sleep to wait for validity
            time.sleep(1)
            current_time = datetime.now()

        tag_url = utils.get_tag("url", api.get_url())
        tag_api = utils.get_tag("api_key", api.get_api_key())
        self.log_manager.log_warning(
            f"{formatted_name}({api.get_server_name()}) server not available. Is this correct {tag_url} {tag_api}"
        )
        return False

    def __create_plex_server(self, config: dict):
        if (
            "server_name" in config
            and "media_path" in config
            and "plex_url" in config
            and "plex_api_key" in config
            and "tautulli_url" in config
            and "tautulli_api_key" in config
        ):
            plex_api = PlexAPI(
                config["server_name"],
                config["plex_url"],
                config["plex_api_key"],
                config["media_path"],
                self.log_manager
            )
            self.__wait_api_valid(
                plex_api,
                utils.get_formatted_plex()
            )
            self.plex_api_list.append(plex_api)

            tautulli_api = TautulliAPI(
                config["server_name"],
                config["tautulli_url"],
                config["tautulli_api_key"],
                self.log_manager
            )
            self.__wait_api_valid(
                tautulli_api,
                utils.get_formatted_tautulli()
            )
            self.tautulli_api_list.append(tautulli_api)
        else:
            self.log_manager.log_warning(
                f"{utils.get_formatted_plex()}:{utils.get_formatted_tautulli()} configuration error must define server_name, media_path, plex_url, plex_api_key, tautulli_url and tautulli_api_key for a server"
            )

    def __create_emby_server(self, config: dict):
        if (
            "server_name" in config
            and "media_path" in config
            and "emby_url" in config
            and "emby_api_key" in config
            and "jellystat_url" in config
            and "jellystat_api_key" in config
        ):
            # Setup the emby api
            emby_api = EmbyAPI(
                config["server_name"],
                config["emby_url"],
                config["emby_api_key"],
                config["media_path"],
                self.log_manager
            )
            self.__wait_api_valid(
                emby_api,
                utils.get_formatted_emby()
            )
            self.emby_api_list.append(emby_api)

            js_api = JellystatAPI(
                config["server_name"],
                config["jellystat_url"],
                config["jellystat_api_key"],
                self.log_manager
            )
            self.__wait_api_valid(
                js_api,
                utils.get_formatted_jellystat()
            )
            self.jellystat_api_list.append(js_api)
        else:
            self.log_manager.log_warning(
                f"{utils.get_formatted_emby()}:{utils.get_formatted_jellystat()} configuration error must define server_name, media_path, emby_url, emby_api_key, jellystat_url and jellystat_api_key for a server"
            )

    def get_plex_api(self, name: str) -> PlexAPI:
        """
        Returns the PlexAPI instance.

        Returns:
            PlexAPI: The PlexAPI instance, or None if not configured.
        """
        for plex_api in self.plex_api_list:
            if plex_api.get_server_name() == name:
                return plex_api
        return None

    def get_tautulli_api(self, name: str) -> TautulliAPI:
        """
        Returns the TautulliAPI instance.
        Returns:
            TautulliAPI: The TautulliAPI instance, or None if not configured.
        """
        for tautulli_api in self.tautulli_api_list:
            if tautulli_api.get_server_name() == name:
                return tautulli_api
        return None

    def get_emby_api(self, name: str) -> EmbyAPI:
        """
        Returns the EmbyAPI instance.

        Returns:
            EmbyAPI: The EmbyAPI instance, or None if not configured.
        """
        for emby_api in self.emby_api_list:
            if emby_api.get_server_name() == name:
                return emby_api
        return None

    def get_jellystat_api(self, name: str) -> JellystatAPI:
        """
        Returns the JellystatAPI instance.

        Returns:
            JellystatAPI: The JellystatAPI instance, or None if not configured.
        """
        for jellystat_api in self.jellystat_api_list:
            if jellystat_api.get_server_name() == name:
                return jellystat_api
        return None
