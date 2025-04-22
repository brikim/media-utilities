"""
Synchronize Emby Play States
    Synchronize the play status of users across emby servers
"""

from dataclasses import dataclass, field
from logging import Logger
from typing import Any, List
from apscheduler.schedulers.blocking import BlockingScheduler

from common.types import UserEmbyInfo
from common import utils

from service.service_base import ServiceBase

from api.api_manager import ApiManager
from api.emby import EmbyAPI, EmbyUserPlayState
from api.jellystat import JellystatHistoryItem


@dataclass
class UserEmbyConfig:
    """ Single emby server/user pair """
    server_name: str
    user_name: str


@dataclass
class UserEmbyConfigs:
    """ List of Emby configs to be synced """
    user_list: list[UserEmbyConfig] = field(default_factory=list)


@dataclass
class EmbySyncGroup:
    """ List of Emby user infos to be synced """
    user_list: list[UserEmbyInfo] = field(default_factory=list)


class SyncEmbyPlayState(ServiceBase):
    """ Sync Emby Play State Service """
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
            "Sync Emby Play State",
            config,
            api_manager,
            logger,
            scheduler
        )

        self.config_user_list: list[UserEmbyConfigs] = []

        try:
            for emby_user_sync in config["emby_user_sync"]:
                new_emby_configs = UserEmbyConfigs()

                for user in emby_user_sync["user"]:
                    if "server" in user and "user_name" in user:
                        emby_api_valid = self.api_manager.get_emby_api(
                            user["server"]) is not None
                        jellystat_api_valid = self.api_manager.get_jellystat_api(
                            user["server"]) is not None
                        if emby_api_valid and jellystat_api_valid:
                            new_emby_configs.user_list.append(
                                UserEmbyConfig(
                                    user["server"],
                                    user["user_name"]
                                )
                            )
                        else:
                            if not emby_api_valid:
                                self.log_warning(
                                    f"No {utils.get_formatted_emby()} server found for {user['server']} ... Skipping {utils.get_tag('user', user['user_name'])}"
                                )
                            if not jellystat_api_valid:
                                self.log_warning(
                                    f"No {utils.get_formatted_jellystat()} server found for {user['server']} ... Skipping {utils.get_tag('user', user['user_name'])}"
                                )

                if len(new_emby_configs.user_list) > 1:
                    self.config_user_list.append(new_emby_configs)
                else:
                    self.log_warning(
                        "Only 1 user found in user group must have at least 2 to sync"
                    )

        except Exception as e:
            self.log_error(f"Read config {utils.get_tag("error", e)}")

    def __get_sync_groups(self) -> List[EmbySyncGroup]:
        user_list: list[EmbySyncGroup] = []
        for config_user in self.config_user_list:
            new_emby_infos = EmbySyncGroup()
            for config_user in config_user.user_list:
                emby_api = self.api_manager.get_emby_api(
                    config_user.server_name)
                jellystat_api = self.api_manager.get_jellystat_api(
                    config_user.server_name)
                if (
                    emby_api is not None
                    and emby_api.get_valid()
                    and jellystat_api is not None
                    and jellystat_api.get_valid()
                ):
                    user_id = emby_api.get_user_id(
                        config_user.user_name)
                    if user_id != emby_api.get_invalid_item_id():
                        new_emby_infos.user_list.append(
                            UserEmbyInfo(
                                config_user.server_name,
                                config_user.user_name,
                                user_id
                            )
                        )
                    else:
                        self.log_warning(
                            f"No {utils.get_formatted_emby()}({config_user.server_name}) user found for {config_user.user_name} ... Skipping User"
                        )

            if len(new_emby_infos.user_list) > 1:
                user_list.append(new_emby_infos)

        return user_list

    def __sync_user_play_state(
        self,
        emby_api: EmbyAPI,
        current_user_play_state: EmbyUserPlayState,
        jellystat_item: JellystatHistoryItem,
        sync_emby_user: UserEmbyInfo,
        target_name: str
    ) -> str:
        return_target_name: str = ""

        if not current_user_play_state.played:
            sync_emby_api = self.api_manager.get_emby_api(
                sync_emby_user.server_name
            )
            sync_emby_item_id = sync_emby_api.get_item_id_from_path(
                current_user_play_state.item_path.replace(
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
                    and current_user_play_state.playback_position_ticks != sync_user_play_state.playback_position_ticks
                ):
                    sync_emby_api.set_play_state(
                        sync_emby_user.user_id,
                        sync_emby_item_id,
                        current_user_play_state.playback_position_ticks,
                        jellystat_item.activity_date
                    )

                    return_target_name = utils.build_target_string(
                        target_name,
                        f"{utils.get_formatted_emby()}({sync_emby_user.server_name}):{sync_emby_user.user_name}",
                        ""
                    )

        return return_target_name

    def __sync_emby_group(self, sync_group: EmbySyncGroup):
        for user in sync_group.user_list:
            emby_api = self.api_manager.get_emby_api(user.server_name)
            jellystat_api = self.api_manager.get_jellystat_api(
                user.server_name
            )
            history_items = jellystat_api.get_user_watch_history(
                user.user_id
            )

            if (history_items != jellystat_api.get_invalid_type()):
                for item in history_items.items:
                    target_name: str = ""
                    user_play_state: EmbyUserPlayState = None

                    if item.series_name:
                        user_play_state = emby_api.get_user_play_state(
                            user.user_id, item.episode_id
                        )
                    else:
                        user_play_state = emby_api.get_user_play_state(
                            user.user_id, item.id
                        )

                    if user_play_state is not None:
                        for sync_user in sync_group.user_list:
                            if sync_user.server_name != user.server_name:
                                target_name = self.__sync_user_play_state(
                                    emby_api, user_play_state, item, sync_user, target_name
                                )

                        if target_name:
                            full_title = f"{item.series_name} - {item.name}" if item.series_name else item.name
                            self.log_info(
                                f"{utils.get_formatted_emby()}({user.server_name}):{user.user_name} watched {int(user_play_state.playback_percentage)}% of {full_title} sync {target_name}"
                            )

    def __sync_emby_play_state(self):
        sync_groups = self.__get_sync_groups()
        for sync_group in sync_groups:
            self.__sync_emby_group(sync_group)

    def init_scheduler_jobs(self):
        if len(self.config_user_list) > 0:
            self.__sync_emby_play_state()
            if self.cron is not None:
                self.log_service_enabled()

                self.scheduler.add_job(
                    self.__sync_emby_play_state,
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
