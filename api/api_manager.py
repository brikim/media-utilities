""" Api Manager """

from logging import Logger
from common import utils

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
        logger: Logger
    ):
        """
        Initializes the ApiManager and establishes connections to configured media servers.
        """
        self.plex_api_list: list[PlexAPI] = []
        self.tautulli_api_list: list[TautulliAPI] = []
        self.emby_api_list: list[EmbyAPI] = []
        self.jellystat_api_list: list[JellystatAPI] = []
        self.logger = logger

        if "plex" in config and "servers" in config["plex"]:
            for server in config["plex"]["servers"]:
                if (
                    "server_name" in server
                    and "media_path" in server
                    and "plex_url" in server
                    and "plex_api_key" in server
                    and "tautulli_url" in server
                    and "tautulli_api_key" in server
                ):
                    self.plex_api_list.append(
                        PlexAPI(
                            server["server_name"],
                            server["plex_url"],
                            server["plex_api_key"],
                            server["media_path"],
                            self.logger
                        )
                    )
                    self.tautulli_api_list.append(
                        TautulliAPI(
                            server["server_name"],
                            server["tautulli_url"],
                            server["tautulli_api_key"],
                            self.logger
                        )
                    )

                    if self.plex_api_list[-1].get_valid():
                        self.logger.info(
                            f"Connected to {utils.get_formatted_plex()}({self.plex_api_list[-1].get_server_reported_name()}) successfully"
                        )
                    else:
                        tag_plex_url = utils.get_tag(
                            "url", server["plex_url"]
                        )
                        tag_plex_api = utils.get_tag(
                            "api_key", server["plex_api_key"]
                        )
                        self.logger.warning(
                            f"{utils.get_formatted_plex()}({server["server_name"]}) server not available. Is this correct {tag_plex_url} {tag_plex_api}"
                        )

                    if self.tautulli_api_list[-1].get_valid():
                        logger.info(
                            f"Connected to {utils.get_formatted_tautulli()}({self.tautulli_api_list[-1].get_server_reported_name()}) successfully"
                        )
                    else:
                        tag_tautulli_url = utils.get_tag(
                            "url", server["tautulli_url"])
                        tag_tautulli_api = utils.get_tag(
                            "api_key", server["tautulli_api_key"])
                        logger.warning(
                            f"{utils.get_formatted_tautulli()}({server["server_name"]}) not available. Is this correct {tag_tautulli_url} {tag_tautulli_api}"
                        )

                else:
                    self.logger.warning(
                        f"{utils.get_formatted_plex()}:{utils.get_formatted_tautulli()} configuration error must define server_name, media_path, plex_url, plex_api_key, tautulli_url and tautulli_api_key for a server"
                    )

        if "emby" in config and "servers" in config["emby"]:
            for server in config["emby"]["servers"]:
                if (
                    "server_name" in server
                    and "media_path" in server
                    and "emby_url" in server
                    and "emby_api_key" in server
                    and "jellystat_url" in server
                    and "jellystat_api_key" in server
                ):
                    self.emby_api_list.append(
                        EmbyAPI(
                            server["server_name"],
                            server["emby_url"],
                            server["emby_api_key"],
                            server["media_path"],
                            self.logger
                        )
                    )
                    self.jellystat_api_list.append(
                        JellystatAPI(
                            server["server_name"],
                            server["jellystat_url"],
                            server["jellystat_api_key"],
                            self.logger
                        )
                    )

                    if self.emby_api_list[-1].get_valid():
                        self.logger.info(
                            f"Connected to {utils.get_formatted_emby()}({self.emby_api_list[-1].get_server_reported_name()}) successfully"
                        )
                    else:
                        tag_emby_url = utils.get_tag(
                            "url", server["emby_url"]
                        )
                        tag_emby_api = utils.get_tag(
                            "api_key", server["emby_api_key"]
                        )
                        self.logger.warning(
                            f"{utils.get_formatted_emby()}({self.emby_api_list[-1].get_server_name()}) server not available. Is this correct {tag_emby_url} {tag_emby_api}"
                        )

                    if self.jellystat_api_list[-1].get_valid():
                        logger.info(
                            f"Connected to {utils.get_formatted_jellystat()}({self.jellystat_api_list[-1].get_server_name()}) successfully"
                        )
                    else:
                        tag_jellystat_url = utils.get_tag(
                            "url", server["jellystat_url"])
                        tag_jellystat_api = utils.get_tag(
                            "api_key", server["jellystat_api_key"])
                        logger.warning(
                            f"{utils.get_formatted_jellystat()}({self.jellystat_api_list[-1].get_server_name()}) not available. Is this correct {tag_jellystat_url} {tag_jellystat_api}"
                        )

                else:
                    self.logger.warning(
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
