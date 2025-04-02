""" 
Folder Cleanup Service
    Deletes empty folders and notified media servers
"""

import os
import shutil
from dataclasses import dataclass, field
from typing import List

from logging import Logger
from apscheduler.schedulers.blocking import BlockingScheduler

from common import utils

from service.service_base import ServiceBase

from api.api_manager import ApiManager


@dataclass
class MediaServerInfo:
    server_name: str
    library_name: str


@dataclass
class PathInfo:
    path: str
    plex_server_list: list[MediaServerInfo] = field(default_factory=list)
    emby_server_list: list[MediaServerInfo] = field(default_factory=list)


class FolderCleanup(ServiceBase):
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
            "Folder Cleanup",
            config,
            api_manager,
            logger,
            scheduler
        )

        self.paths: list[PathInfo] = []
        self.ignore_folder_in_empty_check: list[str] = []
        self.ignore_file_in_empty_check: list[str] = []

        try:
            for path in config["paths_to_check"]:
                if "path" in path:
                    path_info = PathInfo(path["path"])

                    for plex_server in path["plex"]:
                        if "server" in plex_server and "library_name" in plex_server:
                            plex_api = self.api_manager.get_plex_api(
                                plex_server["server"])
                            if plex_api is not None:
                                if plex_api.get_valid() and plex_api.get_library(plex_server["library_name"]) == plex_api.get_invalid_type():
                                    self.log_warning(
                                        f"No {utils.get_formatted_plex()}({plex_server['server']}) library found for {plex_server['library_name']}"
                                    )

                                path_info.plex_server_list.append(
                                    MediaServerInfo(
                                        plex_server["server"],
                                        plex_server["library_name"]
                                    )
                                )
                            else:
                                self.log_warning(
                                    f"No {utils.get_formatted_plex()} server found for {plex_server['server']} ... Skipping"
                                )

                    for emby_server in path["emby"]:
                        if "server" in emby_server and "library_name" in emby_server:
                            emby_api = self.api_manager.get_emby_api(
                                emby_server["server"])
                            if emby_api is not None:
                                if emby_api.get_valid() and emby_api.get_library_from_name(emby_server["library_name"]) == emby_api.get_invalid_item_id():
                                    self.log_warning(
                                        f"No {utils.get_formatted_emby()}({emby_server['server']}) library found for {emby_server['library_name']}"
                                    )

                                path_info.emby_server_list.append(
                                    MediaServerInfo(
                                        emby_server["server"],
                                        emby_server["library_name"]
                                    )
                                )
                            else:
                                self.log_warning(
                                    f"No {utils.get_formatted_emby()} server found for {emby_server['server']} ... Skipping"
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

        except Exception as e:
            self.log_error(
                f"Read config {utils.get_tag("error", e)}"
            )

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

    def __check_delete_empty_folders(self):
        deleted_paths: list[PathInfo] = []
        for path in self.paths:
            connections_valid = True
            for plex_server in path.plex_server_list:
                plex_api = self.api_manager.get_plex_api(
                    plex_server.server_name)
                if not plex_api.get_valid():
                    connections_valid = False
                    self.log_warning(plex_api.get_connection_error_log())
                    break

            if connections_valid:
                for emby_server in path.emby_server_list:
                    emby_api = self.api_manager.get_emby_api(
                        emby_server.server_name)
                    if not emby_api.get_valid():
                        connections_valid = False
                        self.log_warning(emby_api.get_connection_error_log())
                        break

            if connections_valid:
                folders_deleted = False

                keep_running: bool = True
                while keep_running:
                    keep_running = False
                    for dirpath, dirnames, filenames in os.walk(path.path, topdown=False):
                        if self.__is_dir_empty(dirnames) and self.__is_files_empty(filenames):
                            self.log_info(
                                f"Deleting empty {utils.get_tag("folder", dirpath)}"
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

            if target_name != "":
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
