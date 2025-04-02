
from datetime import datetime, timezone
from dataclasses import dataclass, field
from logging import Logger
from typing import Any, List
from apscheduler.schedulers.blocking import BlockingScheduler

from common.types import UserInfo, UserEmbyInfo, UserPlexInfo
from common import utils

from service.ServiceBase import ServiceBase

from api.api_manager import ApiManager
from api.emby import EmbyAPI
from api.plex import PlexAPI


@dataclass
class UserPlexConfig:
    server_name: str
    user_name: str
    can_sync: bool


@dataclass
class UserEmbyConfig:
    server_name: str
    user_name: str


@dataclass
class ConfigUserInfo:
    plex_user_list: list[UserPlexConfig] = field(default_factory=list)
    emby_user_list: list[UserEmbyConfig] = field(default_factory=list)


class SyncWatched(ServiceBase):
    def __init__(
        self,
        ansi_code: str,
        api_manager: ApiManager,
        config: Any,
        logger: Logger,
        scheduler: BlockingScheduler
    ):
        super().__init__(
            ansi_code,
            self.__module__,
            config,
            api_manager,
            logger,
            scheduler
        )

        self.config_user_list: list[ConfigUserInfo] = []

        try:
            for user in config["users"]:
                new_config_user = ConfigUserInfo()

                if "plex" in user:
                    for plex_config in user["plex"]:
                        if "server" in plex_config and "user_name" in plex_config:
                            can_sync = "can_sync" in plex_config and plex_config["can_sync"] == "True"
                            plex_api_valid = self.api_manager.get_plex_api(
                                plex_config["server"]) is not None
                            tautulli_api_valid = self.api_manager.get_tautulli_api(
                                plex_config["server"]) is not None
                            if plex_api_valid and tautulli_api_valid:
                                new_config_user.plex_user_list.append(
                                    UserPlexConfig(
                                        plex_config["server"],
                                        plex_config["user_name"],
                                        can_sync
                                    )
                                )
                            else:
                                if not plex_api_valid:
                                    self.log_warning(
                                        f"No {utils.get_formatted_plex()} server found for {plex_config['server']} ... Skipping {utils.get_tag('user', plex_config['user_name'])}"
                                    )
                                if not tautulli_api_valid:
                                    self.log_warning(
                                        f"No {utils.get_formatted_tautulli()} server found for {plex_config['server']} ... Skipping {utils.get_tag('user', plex_config['user_name'])}"
                                    )

                if "emby" in user:
                    for emby_config in user["emby"]:
                        if "server" in emby_config and "user_name" in emby_config:
                            emby_api_valid = self.api_manager.get_emby_api(
                                emby_config["server"]) is not None
                            jellystat_api_valid = self.api_manager.get_jellystat_api(
                                emby_config["server"]) is not None
                            if emby_api_valid and jellystat_api_valid:
                                new_config_user.emby_user_list.append(
                                    UserEmbyConfig(
                                        emby_config["server"],
                                        emby_config["user_name"]
                                    )
                                )
                            else:
                                if not emby_api_valid:
                                    self.log_warning(
                                        f"No {utils.get_formatted_emby()} server found for {emby_config['server']} ... Skipping {utils.get_tag('user', emby_config['user_name'])}"
                                    )
                                if not jellystat_api_valid:
                                    self.log_warning(
                                        f"No {utils.get_formatted_jellystat()} server found for {emby_config['server']} ... Skipping {utils.get_tag('user', emby_config['user_name'])}"
                                    )

                if (len(new_config_user.plex_user_list) + len(new_config_user.emby_user_list)) > 1:
                    self.config_user_list.append(new_config_user)
                else:
                    self.log_warning(
                        "Only 1 user found in user group must have at least 2 to sync"
                    )

        except Exception as e:
            self.log_error(f"Read config {utils.get_tag("error", e)}")

    def __get_user_data(self) -> List[UserInfo]:
        user_list: list[UserInfo] = []
        for config_user in self.config_user_list:
            new_user_info = UserInfo()

            for config_plex_user in config_user.plex_user_list:
                plex_api = self.api_manager.get_plex_api(
                    config_plex_user.server_name)
                tautulli_api = self.api_manager.get_tautulli_api(
                    config_plex_user.server_name)
                if (
                    plex_api is not None
                    and plex_api.get_valid()
                    and tautulli_api is not None
                    and tautulli_api.get_valid()
                ):
                    plex_user_info = tautulli_api.get_user_info(
                        config_plex_user.user_name)
                    if plex_user_info != tautulli_api.get_invalid_item():
                        plex_friendly_name: str = ""
                        plex_user_id: str = plex_user_info["user_id"]
                        if (
                            "friendly_name" in plex_user_info
                            and plex_user_info["friendly_name"] is not None
                            and plex_user_info["friendly_name"] != ""
                        ):
                            plex_friendly_name = plex_user_info["friendly_name"]
                        else:
                            plex_friendly_name = config_user.plex_user_name

                        new_user_info.plex_users.append(
                            UserPlexInfo(
                                config_plex_user.server_name,
                                config_plex_user.user_name,
                                plex_friendly_name,
                                plex_user_id,
                                config_plex_user.can_sync
                            )
                        )
                    else:
                        tag_server = utils.get_tag(
                            "server", config_plex_user.server_name)
                        self.log_warning(
                            f"No {utils.get_formatted_plex()} {tag_server} user found for {config_user.plex_user_name} ... Skipping User"
                        )

            for config_emby_user in config_user.emby_user_list:
                emby_api = self.api_manager.get_emby_api(
                    config_emby_user.server_name)
                jellystat_api = self.api_manager.get_jellystat_api(
                    config_emby_user.server_name)
                if (
                    emby_api is not None
                    and emby_api.get_valid()
                    and jellystat_api is not None
                    and jellystat_api.get_valid()
                ):
                    emby_user_id = emby_api.get_user_id(
                        config_emby_user.user_name)
                    if emby_user_id != emby_api.get_invalid_item_id():
                        new_user_info.emby_users.append(
                            UserEmbyInfo(
                                config_emby_user.server_name,
                                config_emby_user.user_name,
                                emby_user_id
                            )
                        )
                    else:
                        tag_server = utils.get_tag(
                            "server", config_emby_user.server_name)
                        self.log_warning(
                            f"No {utils.get_formatted_emby()} {tag_server} user found for {config_emby_user.user_name} ... Skipping User"
                        )

            if (len(new_user_info.plex_users) + len(new_user_info.emby_users)) > 1:
                user_list.append(new_user_info)

        return user_list

    def __get_hours_since_play(
        self,
        use_utc_time: bool,
        play_date_time: datetime
    ) -> int:
        current_date_time = datetime.now(
            timezone.utc) if use_utc_time else datetime.now()
        time_difference = current_date_time - play_date_time
        return (time_difference.days * 24) + (time_difference.seconds / 3600)

    def __set_plex_emby_watched_item(
        self,
        emby_api: EmbyAPI,
        user: UserEmbyInfo,
        item_id: str
    ):
        try:
            emby_api.set_watched_item(user.user_id, item_id)
        except Exception as e:
            self.log_error(
                f"Set {utils.get_formatted_emby()} watched {utils.get_tag("error", e)}"
            )

    def __set_emby_emby_watched_item(
        self,
        sync_emby_api: EmbyAPI,
        sync_user: UserEmbyInfo,
        item_id: str,
    ):
        try:
            sync_emby_api.set_watched_item(sync_user.user_id, item_id)
        except Exception as e:
            self.log_error(
                f"Set {utils.get_formatted_emby()} watched {utils.get_tag("error", e)}"
            )

    def __get_emby_path_from_plex_path(self, plex_api: PlexAPI, emby_api: EmbyAPI, plex_path: str) -> str:
        return plex_path.replace(
            plex_api.get_media_path(),
            emby_api.get_media_path(),
            1
        )

    def __get_plex_path_from_emby_path(self, emby_api: EmbyAPI, plex_api: PlexAPI, emby_path: str) -> str:
        return emby_path.replace(
            emby_api.get_media_path(),
            plex_api.get_media_path(),
            1
        )

    def __get_emby_item_id(self, plex_api: PlexAPI, emby_api: EmbyAPI, tautulli_item: Any) -> str:
        plex_item = plex_api.fetch_item(tautulli_item["rating_key"])
        if plex_item is not plex_api.get_invalid_type():
            if plex_item.locations[0]:
                return emby_api.get_item_id_from_path(
                    self.__get_emby_path_from_plex_path(
                        plex_api,
                        emby_api,
                        plex_item.locations[0]
                    )
                )

        return emby_api.get_invalid_item_id()

    def __sync_emby_with_plex_watch_status(
        self,
        plex_api: PlexAPI,
        tautulli_item: Any,
        user: UserEmbyInfo,
        target_name: str
    ) -> str:
        return_target: str = ""
        emby_api = self.api_manager.get_emby_api(user.server_name)
        emby_item_id = self.__get_emby_item_id(
            plex_api, emby_api, tautulli_item)

        # If the item id is valid and the user has not already watched the item
        if emby_item_id != emby_api.get_invalid_item_id():
            emby_watched_status = emby_api.get_watched_status(
                user.user_id, emby_item_id)
            if emby_watched_status is not None and not emby_watched_status:
                self.__set_plex_emby_watched_item(
                    emby_api,
                    user,
                    emby_item_id
                )

                return_target = utils.build_target_string(
                    target_name,
                    f"{utils.get_emby_ansi_code()}({emby_api.get_server_name()})",
                    ""
                )

        return return_target

    def __sync_plex_watch_status(
        self,
        current_user: UserPlexInfo,
        user: UserInfo,
        date_time_for_history: str
    ):
        try:
            plex_api = self.api_manager.get_plex_api(current_user.server_name)
            tautulli_api = self.api_manager.get_tautulli_api(
                current_user.server_name)
            watch_history_data = tautulli_api.get_watch_history_for_user(
                current_user.user_id,
                date_time_for_history
            )

            for history_item in watch_history_data:
                if history_item["watched_status"] == 1:
                    target_name: str = ""
                    for plex_user in user.plex_users:
                        if (
                            plex_user.user_name != current_user.user_name
                            and plex_user.can_sync
                        ):
                            # todo future capability
                            pass

                    for emby_user in user.emby_users:
                        target_name = self.__sync_emby_with_plex_watch_status(
                            plex_api, history_item, emby_user, target_name
                        )

                    if target_name:
                        self.log_info(
                            f"{current_user.friendly_name} watched {history_item["full_title"]} on {utils.get_formatted_plex()}({current_user.server_name}) sync {target_name} watch status"
                        )
        except Exception as e:
            self.log_error(
                f"Get {utils.get_formatted_plex()} history {utils.get_tag("error", e)}"
            )

    def __set_plex_show_watched(
        self,
        emby_api: EmbyAPI,
        emby_series_path: str,
        emby_episode_item: Any,
        user: UserPlexInfo
    ) -> bool:
        return_watched: bool = False
        try:
            plex_api = self.api_manager.get_plex_api(user.server_name)
            cleaned_show_name = utils.remove_year_from_name(
                emby_episode_item["SeriesName"]).lower()
            results = plex_api.search(
                cleaned_show_name,
                plex_api.get_media_type_show_name()
            )

            for item in results:
                plex_show_path = self.__get_plex_path_from_emby_path(
                    emby_api, plex_api, emby_series_path)
                if plex_show_path == item.locations[0]:
                    # Search for the show
                    show = plex_api.get_library_item(
                        item.librarySectionTitle, item.title
                    )

                    if show is not plex_api.get_invalid_type():
                        episode = show.episode(
                            season=emby_episode_item["ParentIndexNumber"],
                            episode=emby_episode_item["IndexNumber"]
                        )

                        plex_episode_location = self.__get_plex_path_from_emby_path(
                            emby_api,
                            plex_api,
                            emby_episode_item["Path"]
                        )

                        if (
                            episode is not None
                            and not episode.isWatched
                            and episode.locations[0] == plex_episode_location
                        ):
                            episode.markWatched()
                            return_watched = True

                        break
        except Exception as e:
            self.log_error(
                f"Error with {utils.get_formatted_plex()}:{user.server_name} movie watched {utils.get_tag("error", e)}"
            )

        return return_watched

    def __set_plex_movie_watched(
        self,
        emby_api: EmbyAPI,
        emby_item: Any,
        user: UserPlexInfo
    ) -> bool:
        marked_watched = False
        try:
            plex_api = self.api_manager.get_plex_api(user.server_name)
            lower_title = emby_item["Name"].lower()
            result_items = plex_api.search(
                lower_title,
                plex_api.get_media_type_movie_name()
            )

            for item in result_items:
                plex_movie_location = self.__get_plex_path_from_emby_path(
                    emby_api, plex_api, emby_item["Path"])
                if plex_movie_location == item.locations[0]:
                    if not item.isWatched:
                        media_item = plex_api.get_library_item(
                            item.librarySectionTitle, item.title)
                        if media_item is not plex_api.get_invalid_type():
                            media_item.markWatched()
                            marked_watched = True

                    break
        except Exception as e:
            self.log_error(
                f"Error with {utils.get_formatted_plex()} movie watched {utils.get_tag("error", e)}"
            )

        return marked_watched

    def __sync_plex_with_emby_watch_status(
        self,
        emby_api: EmbyAPI,
        current_user: UserEmbyInfo,
        jellystat_item: Any,
        plex_user: UserPlexInfo,
        target_name: str
    ) -> str:
        return_target_name: str = ""
        if (jellystat_item["SeriesName"] is not None):
            emby_watched_status = emby_api.get_watched_status(
                current_user.user_id,
                jellystat_item["EpisodeId"]
            )
            if (emby_watched_status is not None and emby_watched_status):
                emby_series_item = emby_api.search_item(
                    jellystat_item["NowPlayingItemId"]
                )
                emby_episode_item = emby_api.search_item(
                    jellystat_item["EpisodeId"]
                )
                if emby_series_item is not None and emby_episode_item is not None:
                    if self.__set_plex_show_watched(
                        emby_api,
                        emby_series_item["Path"],
                        emby_episode_item,
                        plex_user
                    ):
                        return_target_name = utils.build_target_string(
                            target_name,
                            f"{utils.get_plex_ansi_code()}({plex_user.server_name})",
                            ""
                        )
        else:
            emby_watched_status = emby_api.get_watched_status(
                current_user.user_id,
                jellystat_item["NowPlayingItemId"]
            )

            # Check that the item has been marked as watched by emby
            if emby_watched_status is not None and emby_watched_status:
                emby_item = emby_api.search_item(
                    jellystat_item["NowPlayingItemId"]
                )

                if (
                    emby_item is not None
                    and emby_item["Type"] == emby_api.get_media_type_movie_name()
                ):
                    if self.__set_plex_movie_watched(emby_api, emby_item, plex_user):
                        return_target_name = utils.build_target_string(
                            target_name,
                            f"{utils.get_formatted_plex()}({plex_user.server_name})",
                            ""
                        )

        return return_target_name

    def __sync_emby_with_emby_watch_status(
        self,
        emby_api: EmbyAPI,
        current_user: UserEmbyInfo,
        jellystat_item: Any,
        sync_emby_user: UserEmbyInfo,
        target_name: str
    ) -> str:
        return_target_name: str = ""
        sync_emby_api = self.api_manager.get_emby_api(
            sync_emby_user.server_name
        )
        emby_item: Any = None

        if jellystat_item["SeriesName"] is not None:
            emby_watched_status = emby_api.get_watched_status(
                current_user.user_id,
                jellystat_item["EpisodeId"]
            )
            emby_item = emby_api.search_item(jellystat_item["EpisodeId"])
        else:
            emby_watched_status = emby_api.get_watched_status(
                current_user.user_id,
                jellystat_item["NowPlayingItemId"]
            )
            emby_item = emby_api.search_item(
                jellystat_item["NowPlayingItemId"]
            )

        if (
            emby_watched_status is not None
            and emby_watched_status
            and emby_item is not None
        ):
            sync_emby_item_id = sync_emby_api.get_item_id_from_path(
                emby_item["Path"].replace(
                    emby_api.get_media_path(),
                    sync_emby_api.get_media_path(),
                    1
                )
            )

            # If the item id is valid and the user has not already watched the item
            if sync_emby_item_id != sync_emby_api.get_invalid_item_id():
                sync_emby_watched_status = sync_emby_api.get_watched_status(
                    sync_emby_user.user_id, sync_emby_item_id
                )
                if sync_emby_watched_status is not None and not sync_emby_watched_status:
                    self.__set_emby_emby_watched_item(
                        sync_emby_api,
                        sync_emby_user,
                        sync_emby_item_id
                    )

                    return_target_name = utils.build_target_string(
                        target_name,
                        f"{utils.get_emby_ansi_code()}({sync_emby_user.server_name})",
                        ""
                    )

        return return_target_name

    def __sync_emby_watch_status(self, current_user: UserEmbyInfo, user: UserInfo):
        try:
            emby_api = self.api_manager.get_emby_api(current_user.server_name)
            jellystat_api = self.api_manager.get_jellystat_api(
                current_user.server_name
            )
            history_items = jellystat_api.get_user_watch_history(
                current_user.user_id
            )

            if (
                history_items != jellystat_api.get_invalid_type()
                and len(history_items) > 0
            ):
                for item in history_items:
                    hours_since_play = self.__get_hours_since_play(
                        True,
                        datetime.fromisoformat(
                            item["ActivityDateInserted"]
                        )
                    )
                    if hours_since_play <= 24:
                        target_name: str = ""
                        for plex_user in user.plex_users:
                            target_name = self.__sync_plex_with_emby_watch_status(
                                emby_api, current_user, item, plex_user, target_name
                            )

                        for emby_user in user.emby_users:
                            if current_user.server_name != emby_user.server_name:
                                target_name = self.__sync_emby_with_emby_watch_status(
                                    emby_api, current_user, item, emby_user, target_name
                                )

                        if target_name:
                            full_title = f"{item["SeriesName"]} - {item["NowPlayingItemName"]}" if item["SeriesName"] is not None else item["NowPlayingItemName"]
                            self.log_info(
                                f"{current_user.user_name} watched {full_title} on {utils.get_formatted_emby()}({current_user.server_name}) sync {target_name} watch status"
                            )
        except Exception as e:
            self.log_error(
                f"{utils.get_formatted_emby()} watch status {utils.get_tag("error", e)}"
            )

    def __sync_watch_status(self):
        date_time_for_history = utils.get_datetime_for_history_plex_string(1)
        user_list = self.__get_user_data()
        for user in user_list:
            for plex_user in user.plex_users:
                self.__sync_plex_watch_status(
                    plex_user,
                    user,
                    date_time_for_history
                )

            for emby_user in user.emby_users:
                self.__sync_emby_watch_status(emby_user, user)

    def init_scheduler_jobs(self):
        self.__sync_watch_status()
        if len(self.config_user_list) > 0:
            if self.cron is not None:
                self.log_service_enabled()

                self.scheduler.add_job(
                    self.__sync_watch_status,
                    trigger="cron",
                    hour=self.cron.hours,
                    minute=self.cron.minutes
                )
            else:
                self.log_warning(
                    "Enabled but will not Run. Cron is not valid!"
                )
        else:
            self.log_warning("Enabled but no valid users to sync!")
