""" 
DVR Maintainer Service
Deletes shows based on age or number of shows within the folder
"""

import os
import glob
from dataclasses import dataclass, field
from datetime import datetime
from logging import Logger
from typing import List

from apscheduler.schedulers.blocking import BlockingScheduler

from api.api_manager import ApiManager
from common import utils
from service.service_base import ServiceBase


@dataclass
class ShowConfig:
    """ Class representing a show configuration """
    name: str
    action_type: str
    action_value: int


@dataclass
class MediaServerInfo:
    """ Class representing a media server configuration """
    server_name: str
    library_name: str
    library_id: str


@dataclass
class LibraryConfig:
    """ Class representing a library configuration """
    id: int
    utility_path: str
    plex_server_list: list[MediaServerInfo] = field(default_factory=list)
    emby_server_list: list[MediaServerInfo] = field(default_factory=list)
    shows: list[ShowConfig] = field(default_factory=list)


@dataclass
class FileInfo:
    """ Class representing a files information """
    path: str
    age_days: float


class DvrMaintainer(ServiceBase):
    """ Dvr Maintainer Service """

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
            "DVR Maintainer",
            config,
            api_manager,
            logger,
            scheduler
        )

        self.library_configs: list[LibraryConfig] = []
        self.run_test: bool = False

        current_library_id: int = 1

        library_number: int = 1
        for library in config["libraries"]:
            plex_server_list: list[MediaServerInfo] = []
            for plex_server in library["plex"]:
                plex_server_info = self.__read_plex_server_info(
                    plex_server
                )
                if plex_server_info is not None:
                    plex_server_list.append(plex_server_info)

            emby_server_list: list[MediaServerInfo] = []
            for emby_server in library["emby"]:
                emby_server_info = self.__read_emby_server_info(
                    emby_server
                )
                if emby_server_info is not None:
                    emby_server_list.append(emby_server_info)

            # Create the library config for this library
            library_config = LibraryConfig(
                current_library_id,
                library["utilities_path"],
                plex_server_list,
                emby_server_list
            )
            current_library_id += 1

            for show in library["shows"]:
                show_config = self.__read_show_config(show)
                if show_config is not None:
                    library_config.shows.append(show_config)

            if len(library_config.shows) > 0:
                self.library_configs.append(library_config)
            else:
                self.log_error(
                    f"Library {library_number} has no valid shows ... Skipping"
                )

            library_number += 1

    def __read_plex_server_info(self, plex_server: dict) -> MediaServerInfo:
        if "server" in plex_server and "library_name" in plex_server:
            plex_api = self.api_manager.get_plex_api(plex_server["server"])
            if plex_api is not None:
                if (
                    plex_api.get_valid()
                    and not plex_api.get_library_valid(plex_server["library_name"])
                ):
                    self.log_warning(
                        f"No {utils.get_formatted_plex()}({plex_server['server']}) "
                        f"library found for {plex_server['library_name']}"
                    )
                return MediaServerInfo(
                    plex_server["server"],
                    plex_server["library_name"],
                    ""
                )

            self.log_warning(
                f"No {utils.get_formatted_plex()} server found for "
                f"{plex_server['server']} ... Skipping"
            )
        else:
            self.log_warning(
                f"{utils.get_formatted_plex()} config must contain "
                f"{utils.get_tag("tags", "server & library_name")}"
            )
        return None

    def __read_emby_server_info(self, emby_server: dict) -> MediaServerInfo:
        if "server" in emby_server and "library_name" in emby_server:
            emby_api = self.api_manager.get_emby_api(emby_server["server"])
            if emby_api is not None:
                if (
                    emby_api.get_valid()
                    and not emby_api.get_library_valid(emby_server["library_name"])
                ):
                    self.log_warning(
                        f"No {utils.get_formatted_emby()}({emby_server['server']}) "
                        f"library found for {emby_server['library_name']}"
                    )

                return MediaServerInfo(
                    emby_server["server"],
                    emby_server["library_name"],
                    ""
                )

            self.log_warning(
                f"No {utils.get_formatted_emby()} server found for "
                f"{emby_server['server']} ... Skipping"
            )
        else:
            self.log_warning(
                f"{utils.get_formatted_emby()} config must contain "
                f"{utils.get_tag("tags", "server & library_name")}"
            )
        return None

    def __read_show_config(self, show: dict) -> ShowConfig:
        action: str = ""
        action_value = 0

        if "action" in show:
            show_action_name: str = show["action"]

            if show_action_name.find("KEEP_LAST_") != -1:
                action = "KEEP_LAST"
            elif show_action_name.find("KEEP_LENGTH_DAYS_") != -1:
                action = "KEEP_LENGTH_DAYS"
            else:
                self.log_error(
                    f"Unknown show action {show_action_name} ... Skipping"
                )

            if action:
                action_value_str = show_action_name.replace(
                    f"{action}_", ""
                )
                try:
                    action_value = int(action_value_str)
                    return ShowConfig(
                        show["name"],
                        action,
                        action_value
                    )
                except (ValueError, TypeError):
                    self.log_error(
                        f"{action} action type found but "
                        f"{utils.get_tag("value", action_value_str)} not valid!"
                    )
        return None

    def __get_files_in_path(self, path: str) -> List[FileInfo]:
        file_info: list[FileInfo] = []
        for file in glob.glob(f"{path}/**/*", recursive=True):
            if file.endswith(".ts") or file.endswith(".mkv"):
                file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(file))
                file_info.append(
                    FileInfo(file, file_age.days + (file_age.seconds / 86400)))
        return file_info

    def __delete_file(self, pathFileName: str):
        if self.run_test:
            self.log_info(
                f"Running test! Would delete {utils.get_tag("file", pathFileName)}"
            )
        else:
            try:
                os.remove(pathFileName)
            except OSError as e:
                self.log_error(
                    f"Problem deleting "
                    f"{utils.get_tag("file", pathFileName)} "
                    f"{utils.get_tag("error", e)}"
                )

    def __keep_last_delete(self, path: str, keep_last: int) -> bool:
        shows_deleted = False
        file_info = self.__get_files_in_path(path)
        if len(file_info) > keep_last:
            self.log_info(
                f"KEEP_LAST_{keep_last} "
                f"{utils.get_tag("episodes", len(file_info))} "
                f"{utils.get_tag("path", utils.get_standout_text(utils.get_short_path(path)))}"
            )

            sorted_file_info = sorted(
                file_info, key=lambda item: item.age_days, reverse=True)
            shows_to_delete = len(file_info) - keep_last
            deleted_shows = 0
            for file in sorted_file_info:
                file_tag = utils.get_tag(
                    "file",
                    utils.get_standout_text(
                        utils.get_short_path(file.path)
                    )
                )
                self.log_info(
                    f"KEEP_LAST_{keep_last} deleting oldest "
                    f"{utils.get_tag("age days", int(round(file.age_days)))} {file_tag}"
                )
                self.__delete_file(file.path)
                shows_deleted = True
                deleted_shows += 1
                if deleted_shows >= shows_to_delete:
                    break

        return shows_deleted

    def __keep_show_days(self, path: str, keep_days: int) -> bool:
        shows_deleted = False
        file_info = self.__get_files_in_path(path)
        for file in file_info:
            if file.age_days >= keep_days:
                age_days_str = f"{file.age_days:.1f}"
                file_tag = utils.get_tag("file", utils.get_standout_text(
                    utils.get_short_path(file.path)))
                self.log_info(
                    f"KEEP_DAYS_{keep_days} deleting "
                    f"{utils.get_tag("age days", age_days_str)} {file_tag}"
                )
                self.__delete_file(file.path)
                shows_deleted = True
        return shows_deleted

    def __check_library_delete_shows(
        self,
        library: LibraryConfig
    ) -> List[int]:
        deleted_data: list[int] = []
        for show in library.shows:
            library_file_path = f"{library.utility_path}/{show.name}"
            if os.path.exists(library_file_path):
                if show.action_type == "KEEP_LAST":
                    shows_deleted = self.__keep_last_delete(
                        library_file_path,
                        show.action_value
                    )
                    if shows_deleted:
                        deleted_data.append(library.id)
                elif show.action_type == "KEEP_LENGTH_DAYS":
                    shows_deleted = self.__keep_show_days(
                        library_file_path,
                        show.action_value
                    )
                    if shows_deleted:
                        deleted_data.append(library.id)

        return deleted_data

    def __notify_plex_refresh(self, plex_server: MediaServerInfo) -> str:
        plex_api = self.api_manager.get_plex_api(plex_server.server_name)
        plex_api.set_library_scan(plex_server.library_name)
        return f"{utils.get_formatted_plex()}({plex_server.server_name})"

    def __notify_emby_refresh(self, emby_server: MediaServerInfo) -> str:
        emby_api = self.api_manager.get_emby_api(emby_server.server_name)
        emby_api.set_library_scan(emby_server.library_id)
        return f"{utils.get_formatted_emby()}({emby_server.server_name})"

    def __get_library_data(self) -> List[LibraryConfig]:
        library_list: list[LibraryConfig] = []
        for library_config in self.library_configs:
            plex_server_list: list[MediaServerInfo] = []
            for plex_server in library_config.plex_server_list:
                plex_api = self.api_manager.get_plex_api(
                    plex_server.server_name)
                if plex_api.get_valid() and plex_api.get_library_valid(plex_server.library_name):
                    plex_server_list.append(
                        MediaServerInfo(
                            plex_server.server_name,
                            plex_server.library_name,
                            ""
                        )
                    )

            emby_server_list: list[MediaServerInfo] = []
            for emby_server in library_config.emby_server_list:
                emby_api = self.api_manager.get_emby_api(
                    emby_server.server_name)
                library_id = emby_api.get_library_id(emby_server.library_name)
                if emby_api.get_valid() and library_id != emby_api.get_invalid_item_id():
                    emby_server_list.append(
                        MediaServerInfo(
                            emby_server.server_name,
                            emby_server.library_name,
                            library_id
                        )
                    )

            library_list.append(
                LibraryConfig(
                    library_config.id,
                    library_config.utility_path,
                    plex_server_list,
                    emby_server_list,
                    library_config.shows
                )
            )

        return library_list

    def __do_maintenance(self):
        libraries = self.__get_library_data()

        deleted_data_library_ids: list[int] = []
        for library in libraries:
            temp_deleted_library_ids = self.__check_library_delete_shows(
                library)
            for temp_library_id in temp_deleted_library_ids:
                deleted_data_library_ids.append(temp_library_id)

        # Notify media servers of a refresh
        shrunk_deleted_libraries: list[int] = []
        for deleted_data_library_id in deleted_data_library_ids:
            library_in_list: bool = False
            for shrunk_deleted_library_id in shrunk_deleted_libraries:
                if shrunk_deleted_library_id == deleted_data_library_id:
                    library_in_list = True
                    break
            if not library_in_list:
                shrunk_deleted_libraries.append(deleted_data_library_id)

        for deleted_library_id in shrunk_deleted_libraries:
            for library in libraries:
                if library.id == deleted_library_id:
                    target_name: str = ""
                    for plex_server in library.plex_server_list:
                        plex_target_name = self.__notify_plex_refresh(
                            plex_server)
                        target_name = utils.build_target_string(
                            target_name,
                            plex_target_name,
                            plex_server.library_name
                        )

                    for emby_server in library.emby_server_list:
                        emby_target_name = self.__notify_emby_refresh(
                            emby_server)
                        target_name = utils.build_target_string(
                            target_name,
                            emby_target_name,
                            emby_server.library_name
                        )

                    if target_name:
                        self.log_info(
                            f"Notified {target_name} to refresh"
                        )

    def init_scheduler_jobs(self):
        if self.cron is not None:
            self.log_service_enabled()
            self.scheduler.add_job(
                self.__do_maintenance,
                trigger="cron",
                hour=self.cron.hours,
                minute=self.cron.minutes
            )
        else:
            self.log_warning("Enabled but will not Run. Cron is not valid!")
