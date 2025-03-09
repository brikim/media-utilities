
import os
import shutil
from dataclasses import dataclass
from logging import Logger
from typing import Any, List
from apscheduler.schedulers.blocking import BlockingScheduler

from common import utils
from common import utils_server

from service.ServiceBase import ServiceBase

from api.plex import PlexAPI
from api.emby import EmbyAPI

@dataclass
class PathInfo:
    path: str
    plex_library_name: str
    emby_library_name: str
    emby_library_id: str

class FolderCleanup(ServiceBase):
    def __init__(
        self,
        ansi_code: str,
        plex_api: PlexAPI,
        emby_api: EmbyAPI,
        config: Any,
        logger: Logger,
        scheduler: BlockingScheduler
    ):
        super().__init__(
            ansi_code,
            self.__module__,
            config,
            logger,
            scheduler
        )
        
        self.plex_api = plex_api
        self.emby_api = emby_api
        self.paths: list[PathInfo] = []
        self.ignore_folder_in_empty_check: list[str] = []
        self.ignore_file_in_empty_check: list[str] = []
        
        try:
            for path in config["paths_to_check"]:
                plex_library_name = ""
                if "plex_library_name" in path:
                    plex_library_name = path["plex_library_name"]
                
                emby_library_name = ""
                if "emby_library_name" in path:
                    emby_library_name = path["emby_library_name"]
                
                self.paths.append(
                    PathInfo(
                        path["path"],
                        plex_library_name,
                        emby_library_name,
                        ""
                    )
                )
                
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
            connection_info = utils_server.get_connection_info(
                self.plex_api,
                path.plex_library_name,
                self.emby_api,
                path.emby_library_name
            )
            
            if (
                (
                    path.plex_library_name == "" 
                    or connection_info.plex_valid
                ) 
                and (
                    path.emby_library_name == ""
                    or connection_info.emby_valid
                )
            ):
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
                    deleted_paths.append(
                        PathInfo(
                            path.path,
                            path.plex_library_name,
                            path.emby_library_name,
                            connection_info.emby_library_id
                        )
                    )
            else:
                if path.plex_library_name != "" and not connection_info.plex_valid:
                    self.log_warning(self.plex_api.get_connection_error_log())
                if path.emby_library_name != "" and not connection_info.emby_valid:
                    self.log_warning(self.emby_api.get_connection_error_log())
        
        for deleted_path in deleted_paths:
            target_name: str = ""
            if deleted_path.plex_library_name != "":
                self.plex_api.switch_plex_account_admin()
                self.plex_api.set_library_scan(deleted_path.plex_library_name)
                target_name = utils.build_target_string(
                    target_name,
                    utils.get_formatted_plex(),
                    deleted_path.plex_library_name
                )
            if deleted_path.emby_library_id != "":
                self.emby_api.set_library_scan(deleted_path.emby_library_id)
                target_name = utils.build_target_string(
                    target_name,
                    utils.get_formatted_emby(),
                    deleted_path.emby_library_name
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
