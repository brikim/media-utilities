"""
Delete Watched Service
Deletes watched shows set up from a config file.
"""

import os
import math
from datetime import datetime, timezone
from dataclasses import dataclass, field
from logging import Logger
from typing import Any, List

from apscheduler.schedulers.blocking import BlockingScheduler

from api.api_manager import ApiManager
from common import utils
from service.service_base import ServiceBase


@dataclass
class MediaServerLibraryConfigInfo:
    """ Class representing a media server library configuration """
    server_name: str
    library_name: str
    media_path: str
    user_name_list: list[str] = field(default_factory=list)


@dataclass
class LibraryConfigInfo:
    """ Class representing a library configuration """
    id: int
    utilities_path: str
    plex_library_list: list[MediaServerLibraryConfigInfo] = field(
        default_factory=list)
    emby_library_list: list[MediaServerLibraryConfigInfo] = field(
        default_factory=list)


@dataclass
class UserLibraryInfo:
    """ Class representing a user library configuration """
    user_name: str
    friendly_name: str
    user_id: str
    user_id_int: int


@dataclass
class MediaServerLibraryInfo:
    """ Class representing a media server library configuration """
    server_name: str
    library_name: str
    library_id: str
    media_path: str
    user_list: list[UserLibraryInfo] = field(default_factory=list)


@dataclass
class LibraryInfo:
    """ Class representing a library configuration """
    id: int
    utilities_path: str
    plex_library_list: list[MediaServerLibraryInfo] = field(
        default_factory=list)
    emby_library_list: list[MediaServerLibraryInfo] = field(
        default_factory=list)


@dataclass
class DeleteFileInfo:
    """ Class representing a file to delete """
    id: int
    file_path: str
    user_name: str
    player: str


class DeleteWatched(ServiceBase):
    """ Delete Watched Service """

    def __init__(
        self,
        ansi_code: str,
        api_manager: ApiManager,
        config: dict,
        logger: Logger,
        scheduler: BlockingScheduler
    ):
        super().__init__(
            ansi_code,
            "Delete Watched",
            config,
            api_manager,
            logger,
            scheduler
        )

        self.library_configs: list[LibraryConfigInfo] = []
        self.delete_time_hours: int = 24

        try:
            current_id: int = 1
            for library in config["libraries"]:
                if (
                    "utilities_path" in library
                    and ("plex" in library or "emby" in library)
                ):
                    plex_library_list: list[MediaServerLibraryConfigInfo] = []
                    emby_library_list: list[MediaServerLibraryConfigInfo] = []

                    if "plex" in library:
                        for plex_library in library["plex"]:
                            plex_library_config = self.__read_plex_library(
                                plex_library
                            )
                            if plex_library_config is not None:
                                plex_library_list.append(plex_library_config)

                    if "emby" in library:
                        for emby_library in library["emby"]:
                            emby_library_config = self.__read_emby_library(
                                emby_library
                            )
                            if emby_library_config is not None:
                                emby_library_list.append(emby_library_config)

                    if (len(plex_library_list) + len(emby_library_list)) > 0:
                        self.library_configs.append(
                            LibraryConfigInfo(
                                current_id,
                                library["utilities_path"],
                                plex_library_list,
                                emby_library_list
                            )
                        )
                        current_id += 1

            if "delete_time_hours" in config:
                self.delete_time_hours = config["delete_time_hours"]
            self.get_history_days = int(
                math.ceil(self.delete_time_hours / 24) + 1)
        except Exception as e:
            self.log_error(
                f"Read config {utils.get_tag("error", e)}"
            )

    def __read_plex_library(self, plex_library: dict) -> MediaServerLibraryConfigInfo:
        if (
            "server" in plex_library
            and "library_name" in plex_library
            and "media_path" in plex_library
            and "users" in plex_library
        ):
            plex_api = self.api_manager.get_plex_api(plex_library["server"])
            tautulli_api = self.api_manager.get_tautulli_api(
                plex_library["server"])

            if plex_api is not None and tautulli_api is not None:
                plex_server_config = MediaServerLibraryConfigInfo(
                    plex_library["server"],
                    plex_library["library_name"],
                    plex_library["media_path"]
                )

                for plex_user in plex_library["users"]:
                    if "name" in plex_user:
                        plex_server_config.user_name_list.append(
                            plex_user["name"])
                    else:
                        self.log_warning(
                            f"Incomplete {utils.get_formatted_plex()} "
                            f"{utils.get_tag("server", plex_library["server"])} "
                            f"user found must define name ... Skipping"
                        )

                if len(plex_server_config.user_name_list) > 0:
                    return plex_server_config
                else:
                    self.log_warning(
                        f"{utils.get_formatted_plex()}({plex_library["server"]}) "
                        f"config must contain users"
                    )
            else:
                if plex_api is None:
                    self.log_warning(
                        f"No {utils.get_formatted_plex()} server found for "
                        f"{plex_library['server']} ... Skipping"
                    )
                if tautulli_api is None:
                    self.log_warning(
                        f"No {utils.get_formatted_tautulli()} server found for "
                        f"{plex_library['server']} ... Skipping"
                    )
        else:
            self.log_warning(
                f"Incomplete {utils.get_formatted_plex()} library found must define "
                f"server, library_name, media_path and users ... Skipping"
            )
        return None

    def __read_emby_library(self, emby_library: dict) -> MediaServerLibraryConfigInfo:
        if (
            "server" in emby_library
            and "library_name" in emby_library
            and "media_path" in emby_library
            and "users" in emby_library
        ):
            emby_api = self.api_manager.get_emby_api(emby_library["server"])
            js_api = self.api_manager.get_jellystat_api(emby_library["server"])

            if emby_api is not None and js_api is not None:
                emby_server_config = MediaServerLibraryConfigInfo(
                    emby_library["server"],
                    emby_library["library_name"],
                    emby_library["media_path"]
                )

                for emby_user in emby_library["users"]:
                    if "name" in emby_user:
                        emby_server_config.user_name_list.append(
                            emby_user["name"])
                    else:
                        self.log_warning(
                            f"Incomplete {utils.get_formatted_emby()} "
                            f"{utils.get_tag("server", emby_library["server"])} "
                            f"user found must define name ... Skipping"
                        )

                if len(emby_server_config.user_name_list) > 0:
                    return emby_server_config
                else:
                    self.log_warning(
                        f"{utils.get_formatted_emby()}({emby_library["server"]}) config must contain users"
                    )
            else:
                if emby_api is None:
                    self.log_warning(
                        f"No {utils.get_formatted_emby()} server found for "
                        f"{emby_library['server']} ... Skipping"
                    )
                if js_api is None:
                    self.log_warning(
                        f"No {utils.get_formatted_jellystat()} server found for "
                        f"{emby_library['server']} ... Skipping"
                    )
        else:
            self.log_warning(
                f"Incomplete {utils.get_formatted_emby()} library found must define "
                f"server, library_name, media_path and users ... Skipping"
            )
        return None

    def __find_plex_watched_media(
        self,
        lib: MediaServerLibraryInfo,
        lib_id: int,
        utilities_path: str
    ) -> List[DeleteFileInfo]:
        return_deletes: list[DeleteFileInfo] = []
        try:
            tautulli_api = self.api_manager.get_tautulli_api(lib.server_name)
            date_time_string_for_history = utils.get_datetime_for_history_plex_string(
                self.get_history_days)
            for user in lib.user_list:
                if (
                    user.user_name != ""
                    and lib.library_id != ""
                    and lib.media_path != ""
                ):
                    watched_items = tautulli_api.get_watch_history_for_user_and_library(
                        user.user_id_int,
                        lib.library_id,
                        date_time_string_for_history
                    )
                    for item in watched_items.items:
                        if item.watched is not None and item.watched:
                            file_name = tautulli_api.get_filename(item.id)
                            if len(file_name) > 0:
                                item_hours_since_play = utils.get_hours_since_play(
                                    False,
                                    datetime.fromtimestamp(
                                        item.date_watched
                                    )
                                )
                                if item_hours_since_play >= self.delete_time_hours:
                                    return_deletes.append(
                                        DeleteFileInfo(
                                            lib_id,
                                            file_name.replace(
                                                lib.media_path,
                                                utilities_path),
                                            user.friendly_name,
                                            utils.get_formatted_plex()
                                        )
                                    )

        except Exception as e:
            self.log_error(
                f"Find {utils.get_formatted_plex()}({lib.server_name}) watched media "
                f"{utils.get_tag("error", e)}"
            )

        return return_deletes

    def __find_emby_watched_media(
        self,
        lib: MediaServerLibraryInfo,
        lib_id: int,
        utilities_path: str
    ) -> List[DeleteFileInfo]:
        return_deletes: list[DeleteFileInfo] = []
        try:
            if (
                lib.library_name != ""
                and lib.library_id != ""
                and lib.media_path != ""
            ):
                emby_api = self.api_manager.get_emby_api(lib.server_name)
                js_api = self.api_manager.get_jellystat_api(lib.server_name)

                watched_items = js_api.get_library_history(
                    lib.library_id
                )

                for item in watched_items.items:
                    for user in lib.user_list:
                        if user.user_name != "" and item.user_name == user.user_name:
                            item_id = "0"
                            if item.episode_id:
                                item_id = item.episode_id
                            else:
                                item_id = item.id

                            emby_watched_status = emby_api.get_watched_status(
                                user.user_id, item_id
                            )
                            if emby_watched_status is not None and emby_watched_status:
                                item_hours_since_play = utils.get_hours_since_play(
                                    True,
                                    datetime.fromisoformat(item.date_watched)
                                )

                                if item_hours_since_play >= self.delete_time_hours:
                                    emby_item = emby_api.search_item(item_id)
                                    if emby_item is not None:
                                        return_deletes.append(
                                            DeleteFileInfo(
                                                lib_id,
                                                emby_item.path.replace(
                                                    lib.media_path,
                                                    utilities_path),
                                                user.user_name,
                                                utils.get_formatted_emby()
                                            )
                                        )
                            break

        except Exception as e:
            self.log_error(
                f"Find {utils.get_formatted_emby()}({lib.server_name}) "
                f"watched media {utils.get_tag("error", e)}"
            )

        return return_deletes

    def __get_libraries(self) -> List[LibraryInfo]:
        libraries: list[LibraryInfo] = []

        for library_config in self.library_configs:
            plex_library_list: list[MediaServerLibraryInfo] = []
            emby_library_list: list[MediaServerLibraryInfo] = []

            for plex_library_config in library_config.plex_library_list:
                tautulli_api = self.api_manager.get_tautulli_api(
                    plex_library_config.server_name
                )
                if tautulli_api is not None and tautulli_api.get_valid():
                    library_id = tautulli_api.get_library_id(
                        plex_library_config.library_name
                    )
                    if library_id != tautulli_api.get_invalid_type():
                        plex_library_list.append(
                            MediaServerLibraryInfo(
                                plex_library_config.server_name,
                                plex_library_config.library_name,
                                library_id,
                                plex_library_config.media_path
                            )
                        )

                        for plex_user in plex_library_config.user_name_list:
                            plex_user_info = tautulli_api.get_user_info(
                                plex_user
                            )
                            if plex_user_info != tautulli_api.get_invalid_type():
                                friendly_name = plex_user
                                plex_user_id = plex_user_info.id
                                if plex_user_info.friendly_name:
                                    friendly_name = plex_user_info.friendly_name

                                plex_library_list[-1].user_list.append(
                                    UserLibraryInfo(
                                        plex_user,
                                        friendly_name,
                                        "",
                                        plex_user_id
                                    )
                                )
                            else:
                                self.log_warning(
                                    f"{utils.get_formatted_tautulli()}({tautulli_api.get_server_name()}) "
                                    f"could not find {utils.get_tag("user", plex_user)}"
                                )

            for emby_library_config in library_config.emby_library_list:
                emby_api = self.api_manager.get_emby_api(
                    emby_library_config.server_name)
                jellystat_api = self.api_manager.get_jellystat_api(
                    emby_library_config.server_name)
                if (
                    emby_api is not None
                    and emby_api.get_valid()
                    and jellystat_api is not None
                    and jellystat_api.get_valid()
                ):
                    library_id = jellystat_api.get_library_id(
                        emby_library_config.library_name)
                    if library_id != jellystat_api.get_invalid_type():
                        emby_library_list.append(
                            MediaServerLibraryInfo(
                                emby_library_config.server_name,
                                emby_library_config.library_name,
                                library_id,
                                emby_library_config.media_path
                            )
                        )

                        for emby_user in emby_library_config.user_name_list:
                            emby_user_id = emby_api.get_user_id(emby_user)
                            if emby_user_id != emby_api.get_invalid_item_id():
                                emby_library_list[-1].user_list.append(
                                    UserLibraryInfo(
                                        emby_user,
                                        emby_user,
                                        emby_user_id,
                                        None
                                    )
                                )
                            else:
                                self.log_warning(
                                    f"{utils.get_formatted_emby()}({emby_api.get_server_name()}) "
                                    f"could not find {utils.get_tag("user", emby_user)}"
                                )

            libraries.append(
                LibraryInfo(
                    library_config.id,
                    library_config.utilities_path,
                    plex_library_list,
                    emby_library_list
                )
            )

        return libraries

    def __delete_media(self, media_to_delete: list[list[DeleteFileInfo]]) -> list[int]:
        return_libraries: list[int] = []

        for media_container in media_to_delete:
            for media in media_container:
                try:
                    os.remove(media.file_path)
                    self.log_info(
                        f"{media.user_name} watched on {media.player} deleting "
                        f"{utils.get_tag("file", utils.get_standout_text(media.file_path))}"
                    )

                    # Check if this library needs to be added to the list to notify
                    notify_lib_found = False
                    for notify_lib in return_libraries:
                        if notify_lib == media.id:
                            notify_lib_found = True
                            break
                    if not notify_lib_found:
                        return_libraries.append(media.id)
                except Exception as e:
                    self.log_error(
                        f"Failed to delete "
                        f"{utils.get_tag("file", media.file_path)} "
                        f"{utils.get_tag("error", e)}"
                    )

        return return_libraries

    def __notify_plex(self, plex_library_list: list[MediaServerLibraryInfo], target_name) -> str:
        return_target_name: str = target_name
        for plex_library in plex_library_list:
            if plex_library.library_name != "":
                plex_api = self.api_manager.get_plex_api(
                    plex_library.server_name
                )
                plex_api.set_library_scan(
                    plex_library.library_name
                )
                return_target_name = utils.build_target_string(
                    return_target_name,
                    f"{utils.get_formatted_plex()}({plex_library.server_name})",
                    plex_library.library_name
                )
        return return_target_name

    def __notify_emby(self, emby_library_list: list[MediaServerLibraryInfo], target_name) -> str:
        return_target_name: str = target_name
        for emby_library in emby_library_list:
            if emby_library.library_id != "":
                emby_api = self.api_manager.get_emby_api(
                    emby_library.server_name
                )
                emby_api.set_library_scan(
                    emby_library.library_id
                )
                return_target_name = utils.build_target_string(
                    return_target_name,
                    f"{utils.get_formatted_emby()}({emby_library.server_name})",
                    emby_library.library_name
                )
        return return_target_name

    def __check_delete_media(self):
        media_to_delete: list[list[DeleteFileInfo]] = []

        # Get the current libraries to be checked by the service
        libraries = self.__get_libraries()

        # Find media to delete
        for lib in libraries:
            for plex_lib in lib.plex_library_list:
                media_to_delete.append(
                    self.__find_plex_watched_media(
                        plex_lib, lib.id, lib.utilities_path
                    )
                )
            for emby_lib in lib.emby_library_list:
                media_to_delete.append(
                    self.__find_emby_watched_media(
                        emby_lib, lib.id, lib.utilities_path
                    )
                )

        # Delete media added to the list
        libraries_to_notify: list[int] = self.__delete_media(media_to_delete)

        for notify_lib in libraries_to_notify:
            for library in libraries:
                if library.id == notify_lib:
                    target_name = ""

                    target_name = self.__notify_plex(
                        library.plex_library_list, target_name
                    )

                    target_name = self.__notify_emby(
                        library.emby_library_list, target_name
                    )

                    if target_name:
                        self.log_info(f"Notified {target_name} to refresh")

                    break

    def init_scheduler_jobs(self):
        if self.cron is not None:
            self.log_service_enabled()
            self.scheduler.add_job(
                self.__check_delete_media,
                trigger="cron",
                hour=self.cron.hours,
                minute=self.cron.minutes
            )
        else:
            self.log_warning("Enabled but will not Run. Cron is not valid!")
