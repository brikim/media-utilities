""" 
Folder Cleanup Service
Deletes empty folders and notified media servers
"""

import os
import shutil
from dataclasses import dataclass, field
from typing import List

from apscheduler.schedulers.blocking import BlockingScheduler

from api.api_manager import ApiManager
from common import utils
from common.log_manager import LogManager
from service.service_base import ServiceBase


@dataclass
class MediaServerInfo:
    """ Media Server Information """
    server_name: str
    library_name: str


@dataclass
class PathInfo:
    """ Path / Media Server Information """
    path: str
    plex_server_list: list[MediaServerInfo] = field(default_factory=list)
    emby_server_list: list[MediaServerInfo] = field(default_factory=list)


class FolderCleanup(ServiceBase):
    """ Folder Cleanup Service """

    def __init__(
        self,
        api_manager: ApiManager,
        config: dict,
        log_manager: LogManager,
        scheduler: BlockingScheduler
    ):
        super().__init__(
            utils.ANSI_CODE_SERVICE_FOLDER_CLEANUP,
            "Folder Cleanup",
            config,
            api_manager,
            log_manager,
            scheduler
        )

        self.paths: list[PathInfo] = []
        self.ignore_folder_in_empty_check: list[str] = []
        self.ignore_file_in_empty_check: list[str] = []

        for path in config["paths_to_check"]:
            if "path" in path:
                path_info = PathInfo(path["path"])

                for plex_server in path["plex"]:
                    plex_server_info = self.__read_plex_server_info(
                        plex_server
                    )
                    if plex_server_info is not None:
                        path_info.plex_server_list.append(
                            plex_server_info
                        )
                for emby_server in path["emby"]:
                    emby_server_info = self.__read_emby_server_info(
                        emby_server
                    )
                    if emby_server_info is not None:
                        path_info.emby_server_list.append(
                            emby_server_info
                        )

                    self.paths.append(path_info)

        for folder in config["ignore_folder_in_empty_check"]:
            self.ignore_folder_in_empty_check.append(
                folder["ignore_folder"]
            )

        for file in config["ignore_file_in_empty_check"]:
            self.ignore_folder_in_empty_check.append(
                file["ignore_file"]
            )

    def __read_plex_server_info(self, plex_server: dict) -> MediaServerInfo:
        if "server" in plex_server and "library_name" in plex_server:
            plex_api = self.api_manager.get_plex_api(plex_server["server"])
            if plex_api is not None:
                if (plex_api.get_valid()
                        and not plex_api.get_library_valid(plex_server["library_name"])
                    ):
                    self.log_warning(
                        f"No {utils.get_formatted_plex()}({plex_server['server']}) "
                        f"library found for {plex_server['library_name']}"
                    )

                return MediaServerInfo(
                    plex_server["server"],
                    plex_server["library_name"]
                )
            else:
                self.log_warning(
                    f"No {utils.get_formatted_plex()} server found for "
                    f"{plex_server['server']} ... Skipping"
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
                    emby_server["library_name"]
                )
            else:
                self.log_warning(
                    f"No {utils.get_formatted_emby()} server found for "
                    f"{emby_server['server']} ... Skipping"
                )
        return None

    def __is_dir_empty(self, dirnames: List[str]) -> bool:
        dir_empty = True
        for dirname in dirnames:
            if len(self.ignore_folder_in_empty_check) > 0:
                for ignore_dir in self.ignore_folder_in_empty_check:
                    if dirname != ignore_dir:
                        dir_empty = False
                        break
            else:
                dir_empty = False

            if not dir_empty:
                break
        return dir_empty

    def __is_files_empty(self, filenames: List[str]) -> bool:
        filenames_empty: bool = True
        for filename in filenames:
            if len(self.ignore_file_in_empty_check) > 0:
                for ignore_file in self.ignore_file_in_empty_check:
                    if filename != ignore_file:
                        filenames_empty = False
                        break
            else:
                filenames_empty = False

            if not filenames_empty:
                break
        return filenames_empty

    def __check_media_connections_valid(
        self,
        plex_server_list: list[MediaServerInfo],
        emby_server_list: list[MediaServerInfo]
    ) -> bool:
        connections_valid: bool = True

        for plex_server in plex_server_list:
            plex_api = self.api_manager.get_plex_api(
                plex_server.server_name)
            if not plex_api.get_valid():
                connections_valid = False
                self.log_warning(plex_api.get_connection_error_log())
                break

        if connections_valid:
            for emby_server in emby_server_list:
                emby_api = self.api_manager.get_emby_api(
                    emby_server.server_name)
                if not emby_api.get_valid():
                    connections_valid = False
                    self.log_warning(emby_api.get_connection_error_log())
                    break

        return connections_valid

    def __check_delete_empty_folders(self):
        deleted_paths: list[PathInfo] = []
        for path in self.paths:
            if self.__check_media_connections_valid(
                path.plex_server_list,
                path.emby_server_list
            ):
                folders_deleted = False

                keep_running: bool = True
                while keep_running:
                    keep_running = False
                    for dirpath, dirnames, filenames in os.walk(path.path, topdown=False):
                        if self.__is_dir_empty(dirnames) and self.__is_files_empty(filenames):
                            self.log_info(
                                f"Deleting empty "
                                f"{utils.get_tag("folder", utils.get_standout_text(dirpath))}"
                            )
                            shutil.rmtree(dirpath, ignore_errors=True)
                            keep_running = True
                            folders_deleted = True

                if folders_deleted:
                    deleted_paths.append(path)
            else:
                self.log_warning(
                    f"Skipping {utils.get_tag("path", path.path)} due to invalid connections"
                )

        for deleted_path in deleted_paths:
            target_name: str = ""

            for plex_server in deleted_path.plex_server_list:
                plex_api = self.api_manager.get_plex_api(
                    plex_server.server_name)
                plex_api.set_library_scan(plex_server.library_name)
                target_name = utils.build_target_string(
                    target_name,
                    f"{utils.get_formatted_plex()}({plex_server.server_name})",
                    plex_server.library_name
                )

            for emby_server in deleted_path.emby_server_list:
                emby_api = self.api_manager.get_emby_api(
                    emby_server.server_name)
                emby_api.set_library_scan(emby_server.library_name)
                target_name = utils.build_target_string(
                    target_name,
                    f"{utils.get_formatted_emby()}({emby_server.server_name})",
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
                self.__check_delete_empty_folders,
                trigger="cron",
                hour=self.cron.hours,
                minute=self.cron.minutes
            )
        else:
            self.log_warning("Enabled but will not Run. Cron is not valid!")
