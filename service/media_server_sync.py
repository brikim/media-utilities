"""
Media Server Synchronize Service
    Synchronize watch and play state between media servers. 
    Uses Plex with Tautulli and Emby with Jellystat
"""

from datetime import datetime
from dataclasses import dataclass, field
from logging import Logger
from typing import Any, List
from apscheduler.schedulers.blocking import BlockingScheduler

from common.types import UserInfo, UserEmbyInfo, UserPlexInfo
from common import utils

from service.service_base import ServiceBase

from api.api_manager import ApiManager
from api.emby import EmbyAPI, EmbyItem, EmbyUserPlayState
from api.plex import PlexAPI
from api.jellystat import JellystatHistoryItem
from api.tautulli import TautulliHistoryItem


@dataclass
class ConfigPlexUser:
    """ Plex Configuration for a User """
    server_name: str
    user_name: str
    can_sync: bool


@dataclass
class ConfigEmbyUser:
    """ Emby Configuration for a User """
    server_name: str
    user_name: str


@dataclass
class ConfigUserInfo:
    """ Configuration for a User """
    plex_user_list: list[ConfigPlexUser] = field(default_factory=list)
    emby_user_list: list[ConfigEmbyUser] = field(default_factory=list)


class MediaServerSync(ServiceBase):
    """ Media Server Sync Service """

    def __init__(
        self,
        ansi_code: str,
        api_manager: ApiManager,
        config: Any,
        logger: Logger,
        scheduler: BlockingScheduler
    ):
        """ Media Server Sync Initializer """
        super().__init__(
            ansi_code,
            "Media Server Sync",
            config,
            api_manager,
            logger,
            scheduler
        )

        self.config_user_list: list[ConfigUserInfo] = []

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
                                ConfigPlexUser(
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
                                ConfigEmbyUser(
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

    def __get_user_data(self) -> List[UserInfo]:
        """ Get User Data from the servers based on the configuration """
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
                    if plex_user_info != tautulli_api.get_invalid_type():
                        plex_friendly_name: str = ""
                        plex_user_id: str = plex_user_info.id
                        if plex_user_info.friendly_name:
                            plex_friendly_name = plex_user_info.friendly_name
                        else:
                            plex_friendly_name = config_plex_user.user_name

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
                        self.log_warning(
                            f"No {utils.get_formatted_plex()}({config_plex_user.server_name}) user found for {config_plex_user.user_name} ... Skipping User"
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
                        self.log_warning(
                            f"No {utils.get_formatted_emby()}({config_emby_user.server_name}) user found for {config_emby_user.user_name} ... Skipping User"
                        )

            if (len(new_user_info.plex_users) + len(new_user_info.emby_users)) > 1:
                user_list.append(new_user_info)

        return user_list

    def __set_emby_watch_state(
        self,
        emby_api: EmbyAPI,
        user: UserEmbyInfo,
        item_id: str,
    ):
        """ Set the state of an Emby item for a user as watched """
        emby_api.set_watched_item(user.user_id, item_id)

    def __get_emby_path_from_plex_path(self, plex_api: PlexAPI, emby_api: EmbyAPI, plex_path: str) -> str:
        """ Get the Emby path from the Plex path """
        return plex_path.replace(
            plex_api.get_media_path(),
            emby_api.get_media_path(),
            1
        )

    def __get_plex_path_from_emby_path(self, emby_api: EmbyAPI, plex_api: PlexAPI, emby_path: str) -> str:
        """ Get the Plex path from the Emby path """
        return emby_path.replace(
            emby_api.get_media_path(),
            plex_api.get_media_path(),
            1
        )

    def __get_emby_item_id_from_plex_item(self, plex_api: PlexAPI, emby_api: EmbyAPI, tautulli_item: TautulliHistoryItem) -> str:
        """ Get the Emby item id from a plex item"""
        plex_path = plex_api.get_item_path(tautulli_item.id)
        if plex_path is not plex_api.get_invalid_type() and plex_path:
            return emby_api.get_item_id_from_path(
                self.__get_emby_path_from_plex_path(
                    plex_api,
                    emby_api,
                    plex_path
                )
            )

        return emby_api.get_invalid_item_id()

    def __sync_emby_user_with_plex_watch_state(
        self,
        plex_api: PlexAPI,
        tautulli_item: TautulliHistoryItem,
        sync_emby_user: UserEmbyInfo,
        target_name: str
    ) -> str:
        """ Sync the Emby user to a specificPlex users watch state """
        return_target: str = ""

        sync_emby_api = self.api_manager.get_emby_api(
            sync_emby_user.server_name)
        sync_emby_item_id = self.__get_emby_item_id_from_plex_item(
            plex_api, sync_emby_api, tautulli_item)

        # If the item id is valid and the user has not already watched the item
        if sync_emby_item_id != sync_emby_api.get_invalid_item_id():
            emby_watched_status = sync_emby_api.get_watched_status(
                sync_emby_user.user_id, sync_emby_item_id)
            if emby_watched_status is not None and not emby_watched_status:
                self.__set_emby_watch_state(
                    sync_emby_api,
                    sync_emby_user,
                    sync_emby_item_id
                )

                return_target = utils.build_target_string(
                    target_name,
                    f"{utils.get_formatted_emby()}({sync_emby_api.get_server_name()})",
                    ""
                )

        return return_target

    def __log_watch_state_update(
        self,
        play_server_type: str,
        play_server: str,
        play_user_name: str,
        played_item_name: str,
        target_name: str
    ):
        """ Log a watch state update """
        self.log_info(
            f"{play_server_type}({play_server}):{play_user_name} watched {utils.get_standout_text(played_item_name)} sync {target_name} watch state"
        )
        
    def __log_play_state_update(
        self,
        play_server_type: str,
        play_server: str,
        play_user_name: str,
        percentage: int,
        played_item_name: str,
        target_name: str
    ):
        """ Log a play state update """
        self.log_info(
            f"{play_server_type}({play_server}):{play_user_name} played {percentage}% of {utils.get_standout_text(played_item_name)} sync {target_name} play state"
        )
        
    def __sync_emby_with_plex_watched_state(
        self,
        plex_api: PlexAPI,
        history_item: TautulliHistoryItem,
        emby_users: List[UserEmbyInfo],
        target_name: str
    ) -> str:
        return_target_name: str = ""

        for sync_emby_user in emby_users:
            return_target_name = self.__sync_emby_user_with_plex_watch_state(
                plex_api, history_item, sync_emby_user, target_name
            )

        return return_target_name

    def __sync_plex_watch_state(
        self,
        plex_api: PlexAPI,
        current_user: UserPlexInfo,
        history_item: TautulliHistoryItem,
        user: UserInfo
    ):
        """ Sync Plex watch state """
        target_name: str = ""

        for sync_plex_user in user.plex_users:
            if (
                current_user.server_name != sync_plex_user.server_name
                and sync_plex_user.can_sync
            ):
                # todo future capability
                pass

        target_name = self.__sync_emby_with_plex_watched_state(
            plex_api,
            history_item,
            user.emby_users,
            target_name
        )

        if target_name:
            self.__log_watch_state_update(
                utils.get_formatted_plex(),
                current_user.server_name,
                current_user.friendly_name,
                history_item.full_name,
                target_name
            )

    def __sync_emby_user_with_plex_play_state(
        self,
        plex_api: PlexAPI,
        tautulli_item: TautulliHistoryItem,
        sync_emby_user: UserEmbyInfo,
        target_name: str
    ) -> str:
        """ Sync the Emby users to a specific Emby user play state """
        return_target_name: str = ""

        sync_emby_api = self.api_manager.get_emby_api(
            sync_emby_user.server_name
        )

        sync_emby_item_id = self.__get_emby_item_id_from_plex_item(
            plex_api, sync_emby_api, tautulli_item
        )

        # If the item id is valid and the user has not already watched the item
        if sync_emby_item_id != sync_emby_api.get_invalid_item_id():
            sync_user_play_state = sync_emby_api.get_user_play_state(
                sync_emby_user.user_id, sync_emby_item_id
            )
            emby_item = sync_emby_api.search_item(sync_emby_item_id)
            if (
                sync_user_play_state is not None
                and emby_item is not None
                and tautulli_item.playback_percentage != round(sync_user_play_state.playback_percentage)
            ):
                # Get the play location ticks
                emby_tick_location: int = int(emby_item.run_time_ticks * (
                    tautulli_item.playback_percentage / 100
                ))
                
                # Set the emby play state for this user
                sync_emby_api.set_play_state(
                    sync_emby_user.user_id,
                    sync_emby_item_id,
                    emby_tick_location,
                    utils.convert_epoch_time_to_emby_time_string(tautulli_item.date_watched)
                )

                return_target_name = utils.build_target_string(
                    target_name,
                    f"{utils.get_formatted_emby()}({sync_emby_user.server_name})",
                    ""
                )

        return return_target_name
    
    def __sync_emby_with_plex_play_state(
        self,
        plex_api: PlexAPI,
        history_item: TautulliHistoryItem,
        emby_users: List[UserEmbyInfo],
        target_name: str
    ) -> str:
        return_target_name: str = target_name

        for sync_emby_user in emby_users:
            return_target_name = self.__sync_emby_user_with_plex_play_state(
                plex_api, history_item, sync_emby_user, return_target_name
            )

        return return_target_name
    
    def __sync_plex_play_state(
        self,
        plex_api: PlexAPI,
        current_user: UserPlexInfo,
        history_item: TautulliHistoryItem,
        user: UserInfo
    ):
        """ Sync Plex play state """
        target_name: str = ""

        # Currently only Emby API supports syncing play state
        target_name = self.__sync_emby_with_plex_play_state(
            plex_api,
            history_item,
            user.emby_users,
            target_name
        )
        
        if target_name:
            self.__log_play_state_update(
                utils.get_formatted_plex(),
                current_user.server_name,
                current_user.friendly_name,
                int(history_item.playback_percentage),
                history_item.full_name,
                target_name
            )

    def __sync_plex_state(
        self,
        current_user: UserPlexInfo,
        user: UserInfo,
        date_time_for_history: str
    ):
        """ For a specific plex user find watched items and sync corresponding emby users watch state """
        plex_api = self.api_manager.get_plex_api(current_user.server_name)
        tautulli_api = self.api_manager.get_tautulli_api(
            current_user.server_name)
        watch_history_data = tautulli_api.get_watch_history_for_user(
            current_user.user_id,
            date_time_for_history
        )

        for history_item in watch_history_data.items:
            if history_item.watched is not None and history_item.watched:
                self.__sync_plex_watch_state(
                    plex_api,
                    current_user,
                    history_item,
                    user
                )
            else:
                self.__sync_plex_play_state(
                    plex_api,
                    current_user,
                    history_item,
                    user
                )

    def __set_plex_show_watched(
        self,
        emby_api: EmbyAPI,
        emby_series_path: str,
        emby_episode_item: EmbyItem,
        user: UserPlexInfo
    ) -> bool:
        """ From an Emby show item sync a Plex user to watched state """
        plex_api = self.api_manager.get_plex_api(user.server_name)
        cleaned_show_name = utils.remove_year_from_name(
            emby_episode_item.series_name
        ).lower()
        plex_show_path = self.__get_plex_path_from_emby_path(
            emby_api, plex_api, emby_series_path
        )
        plex_episode_location = self.__get_plex_path_from_emby_path(
            emby_api, plex_api, emby_episode_item.path
        )

        return plex_api.set_episode_watched(
            cleaned_show_name,
            emby_episode_item.season_num,
            emby_episode_item.episode_num,
            plex_show_path,
            plex_episode_location
        )

    def __set_plex_movie_watched(
        self,
        emby_api: EmbyAPI,
        emby_item: EmbyItem,
        user: UserPlexInfo
    ) -> bool:
        """ From an Emby movie item sync a Plex user to watched state """
        plex_api = self.api_manager.get_plex_api(user.server_name)
        lower_title = emby_item.name.lower()
        plex_movie_location = self.__get_plex_path_from_emby_path(
            emby_api, plex_api, emby_item.path
        )
        return plex_api.set_movie_watched(lower_title, plex_movie_location)

    def __sync_plex_with_emby_watched_state(
        self,
        emby_api: EmbyAPI,
        jellystat_item: JellystatHistoryItem,
        plex_user: UserPlexInfo,
        target_name: str
    ) -> str:
        """ For an Emby watched item sync a Plex user to watched state """
        return_target_name: str = ""

        if jellystat_item.series_name:
            emby_series_item = emby_api.search_item(
                jellystat_item.id
            )
            emby_episode_item = emby_api.search_item(
                jellystat_item.episode_id
            )

            if emby_series_item is not None and emby_episode_item is not None:
                if self.__set_plex_show_watched(
                    emby_api,
                    emby_series_item.path,
                    emby_episode_item,
                    plex_user
                ):
                    return_target_name = utils.build_target_string(
                        target_name,
                        f"{utils.get_formatted_plex()}({plex_user.server_name})",
                        ""
                    )
        else:
            emby_item = emby_api.search_item(
                jellystat_item.id
            )
            if (
                emby_item is not None
                and emby_item.type == emby_api.get_media_type_movie_name()
            ):
                if self.__set_plex_movie_watched(emby_api, emby_item, plex_user):
                    return_target_name = utils.build_target_string(
                        target_name,
                        f"{utils.get_formatted_plex()}({plex_user.server_name})",
                        ""
                    )

        return return_target_name

    def __sync_emby_with_emby_watched_state(
        self,
        emby_api: EmbyAPI,
        jellystat_item: JellystatHistoryItem,
        sync_emby_user: UserEmbyInfo,
        target_name: str
    ) -> str:
        """ Sync Emby watched state to another Emby user instance """
        return_target_name: str = ""

        emby_item = emby_api.search_item(
            jellystat_item.episode_id if jellystat_item.series_name else jellystat_item.id)

        if (emby_item is not None):
            sync_emby_api = self.api_manager.get_emby_api(
                sync_emby_user.server_name
            )
            sync_emby_item_id = sync_emby_api.get_item_id_from_path(
                emby_item.path.replace(
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
                    self.__set_emby_watch_state(
                        sync_emby_api,
                        sync_emby_user,
                        sync_emby_item_id
                    )

                    return_target_name = utils.build_target_string(
                        target_name,
                        f"{utils.get_formatted_emby()}({sync_emby_user.server_name})",
                        ""
                    )

        return return_target_name

    def __sync_emby_watched_state(
        self,
        emby_api: EmbyAPI,
        current_user: UserEmbyInfo,
        jellystat_item: JellystatHistoryItem,
        user: UserInfo
    ):
        """ Set an Emby user watch state from another emby server item """
        target_name: str = ""

        for sync_plex_user in user.plex_users:
            target_name = self.__sync_plex_with_emby_watched_state(
                emby_api, jellystat_item, sync_plex_user, target_name
            )

        for sync_emby_user in user.emby_users:
            if current_user.server_name != sync_emby_user.server_name:
                target_name = self.__sync_emby_with_emby_watched_state(
                    emby_api, jellystat_item, sync_emby_user, target_name
                )

        if target_name:
            full_title = f"{jellystat_item.series_name} - {jellystat_item.name}" if jellystat_item.series_name else jellystat_item.name
            self.__log_watch_state_update(
                utils.get_formatted_emby(),
                current_user.server_name,
                current_user.user_name,
                full_title,
                target_name
            )

    def __sync_emby_with_emby_play_state(
        self,
        emby_api: EmbyAPI,
        current_play_state: EmbyUserPlayState,
        jellystat_item: JellystatHistoryItem,
        sync_emby_user: UserEmbyInfo,
        target_name: str
    ) -> str:
        """ Sync the Emby users to a specific Emby user play state """
        return_target_name: str = ""

        sync_emby_api = self.api_manager.get_emby_api(
            sync_emby_user.server_name
        )

        sync_emby_item_id = sync_emby_api.get_item_id_from_path(
            current_play_state.item_path.replace(
                emby_api.get_media_path(),
                sync_emby_api.get_media_path(),
                1
            )
        )

        # If the item id is valid and the user has not already watched the item
        if sync_emby_item_id != sync_emby_api.get_invalid_item_id():
            sync_user_play_state = sync_emby_api.get_user_play_state(
                sync_emby_user.user_id, sync_emby_item_id
            )
            if (
                sync_user_play_state is not None
                and not sync_user_play_state.played
                and current_play_state.playback_position_ticks != sync_user_play_state.playback_position_ticks
            ):
                sync_emby_api.set_play_state(
                    sync_emby_user.user_id,
                    sync_emby_item_id,
                    current_play_state.playback_position_ticks,
                    jellystat_item.date_watched
                )

                return_target_name = utils.build_target_string(
                    target_name,
                    f"{utils.get_formatted_emby()}({sync_emby_user.server_name})",
                    sync_emby_user.user_name
                )

        return return_target_name

    def __sync_emby_play_state(
        self,
        emby_api: EmbyAPI,
        current_user: UserEmbyInfo,
        current_play_state: EmbyUserPlayState,
        jellystat_item: JellystatHistoryItem,
        emby_user_list: List[UserEmbyInfo]
    ):
        """ Sync a user play state in Emby from another Emby user instance """
        target_name: str = ""

        # Can only sync emby to emby play state currently per available API's
        for sync_emby_user in emby_user_list:
            if current_user.server_name != sync_emby_user.server_name:
                target_name = self.__sync_emby_with_emby_play_state(
                    emby_api,
                    current_play_state,
                    jellystat_item,
                    sync_emby_user,
                    target_name
                )

        if target_name:
            full_title: str = f"{jellystat_item.series_name} - {jellystat_item.name}" if jellystat_item.series_name else jellystat_item.name
            self.__log_play_state_update(
                utils.get_formatted_emby(),
                current_user.server_name,
                current_user.user_name,
                int(current_play_state.playback_percentage),
                full_title,
                target_name
            )

    def __sync_emby_state(self, current_user: UserEmbyInfo, user: UserInfo):
        """ Sync the state of an Emby user to configured media servers """
        emby_api = self.api_manager.get_emby_api(current_user.server_name)
        jellystat_api = self.api_manager.get_jellystat_api(
            current_user.server_name
        )
        history_items = jellystat_api.get_user_watch_history(
            current_user.user_id
        )

        if (history_items != jellystat_api.get_invalid_type()):
            for item in history_items.items:
                hours_since_play = utils.get_hours_since_play(
                    True,
                    datetime.fromisoformat(item.date_watched)
                )
                if hours_since_play <= 24:
                    current_play_state: EmbyUserPlayState = emby_api.get_user_play_state(
                        current_user.user_id,
                        item.episode_id if item.series_name else item.id
                    )
                    # Determine if we need to sync watch state or play state
                    if current_play_state.played:
                        self.__sync_emby_watched_state(
                            emby_api,
                            current_user,
                            item,
                            user
                        )
                    else:
                        self.__sync_emby_play_state(
                            emby_api,
                            current_user,
                            current_play_state,
                            item,
                            user.emby_users
                        )

    def __sync_state(self):
        """ Sync all the configured states """
        date_time_for_history = utils.get_datetime_for_history_plex_string(1)
        user_list = self.__get_user_data()
        for user in user_list:
            for plex_user in user.plex_users:
                self.__sync_plex_state(
                    plex_user,
                    user,
                    date_time_for_history
                )

            for emby_user in user.emby_users:
                self.__sync_emby_state(emby_user, user)

    def init_scheduler_jobs(self):
        """ Initialize all scheduled jobs """
        if len(self.config_user_list) > 0:
            if self.cron is not None:
                self.log_service_enabled()

                self.scheduler.add_job(
                    self.__sync_state,
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
