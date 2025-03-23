
import os
import glob
from datetime import datetime
from logging import Logger
from typing import Any, List
from apscheduler.schedulers.blocking import BlockingScheduler
from dataclasses import dataclass, field

from common import utils

from service.ServiceBase import ServiceBase

from api.plex import PlexAPI
from api.emby import EmbyAPI

@dataclass
class ShowConfig:
    name: str
    action_type: str
    action_value: int

@dataclass
class LibraryConfig:
    id: int
    plex_library_name: str
    emby_library_name: str
    emby_library_id: str
    utility_path: str
    shows: list = field(default_factory=list)
    
@dataclass
class DeletedData:
    library_id: int
    plex_library_name: str
    emby_library_name: str
    emby_library_id: str
@dataclass
class FileInfo:
    path: str
    age_days: float

class DvrMaintainer(ServiceBase):
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
        self.library_configs: list[LibraryConfig] = []
        self.run_test: bool = False
        
        current_library_id: int = 1
        
        try:
            library_number: int = 1
            for library in config["libraries"]:
                plex_library_name = ""
                if "plex_library_name" in library:
                    plex_library_name = library["plex_library_name"]
                
                emby_library_name = ""
                if "emby_library_name" in library:
                    emby_library_name = library["emby_library_name"]
                
                # Create the library config for this library
                library_config = LibraryConfig(
                    current_library_id,
                    plex_library_name,
                    emby_library_name,
                    "",
                    library["utilities_path"]
                )
                current_library_id += 1
                
                for show in library["shows"]:
                    action = ""
                    action_value = 0
                    if show["action"].find("KEEP_LAST_") != -1:
                        action = "KEEP_LAST"
                        action_value = int(
                            show["action"].replace(
                                "KEEP_LAST_", ""
                            )
                        )
                    elif show["action"].find("KEEP_LENGTH_DAYS_") != -1:
                        action = "KEEP_LENGTH_DAYS"
                        action_value = int(
                            show["action"].replace(
                                "KEEP_LENGTH_DAYS_", ""
                            )
                        )
                    
                    if action != "": 
                        library_config.shows.append(
                            ShowConfig(
                                show["name"],
                                action,
                                action_value
                            )
                        )
                    else:
                        self.log_error(
                            f"Unknown show action {show["action"]} ... Skipping"
                        )
                        
                if len(library_config.shows) > 0:
                    self.library_configs.append(library_config)
                else:
                    self.log_error(
                        f"Library {library_number} has no valid shows ... Skipping"
                    )
                    
                library_number += 1

        except Exception as e:
            self.log_error(
                f"Read config {utils.get_tag("error", e)}"
            )
    
    def __get_files_in_path(self, path: str) -> List[FileInfo]:
        file_info: list[FileInfo] = []
        for file in glob.glob(f"{path}/**/*", recursive=True):
            if file.endswith(".ts") or file.endswith(".mkv"):
                file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(file))
                file_info.append(FileInfo(file, file_age.days + (file_age.seconds / 86400)))
        return file_info

    def __delete_file(self, pathFileName: str):
        if self.run_test:
            self.log_info(
                f"Running test! Would delete {utils.get_tag("file", pathFileName)}"
            )
        else:
            try:
                os.remove(pathFileName)
            except Exception as e:
                self.log_error(
                    f"Problem deleting {utils.get_tag("file", pathFileName)} {utils.get_tag("error", e)}"
                )
    
    def __keep_last_delete(self, path: str, keep_last: int) -> bool:
        shows_deleted = False
        file_info = self.__get_files_in_path(path)
        if len(file_info) > keep_last:
            self.log_info(
                f"KEEP_LAST_{keep_last} {utils.get_tag("episodes", len(file_info))} {utils.get_tag("path", path)}"
            )
            try:
                sorted_file_info = sorted(file_info, key=lambda item: item.age_days, reverse=True)
                shows_to_delete = len(file_info) - keep_last
                deleted_shows = 0
                for file in sorted_file_info:
                    self.log_info(
                        "KEEP_LAST_{} deleting oldest {}age days={}{:.1f} {}".format(
                            keep_last,
                            utils.get_tag_ansi_code(),
                            utils.get_log_ansi_code(),
                            file.age_days,
                            utils.get_tag("file", file.path)
                        )
                    )
                    self.__delete_file(file.path)
                    shows_deleted = True

                    deleted_shows += 1
                    if deleted_shows >= shows_to_delete:
                        break
            
            except Exception as e:
                self.log_error(
                    f"KEEP_LAST_{keep_last} error sorting files {utils.get_tag("error", e)}"
                )

        return shows_deleted

    def __keep_show_days(self, path: str, keep_days: int) -> bool:
        shows_deleted = False
        file_info = self.__get_files_in_path(path)
        for file in file_info:
            if file.age_days >= keep_days:
                self.log_info(
                    "KEEP_DAYS_{} deleting {}age days={}{:.1f} {}".format(
                        keep_days,
                        utils.get_tag_ansi_code(),
                        utils.get_log_ansi_code(),
                        file.age_days,
                        utils.get_tag("file", file.path)
                    )
                )
                self.__delete_file(file.path)
                shows_deleted = True
        return shows_deleted

    def __check_library_delete_shows(
        self,
        library: LibraryConfig
    ) -> List[DeletedData]:
        deleted_data: list[DeletedData] = []
        for show in library.shows:
            library_file_path = f"{library.utility_path}/{show.name}"
            if os.path.exists(library_file_path):
                if show.action_type == "KEEP_LAST":
                    try:
                        shows_deleted = self.__keep_last_delete(
                            library_file_path,
                            show.action_value
                        )
                        if shows_deleted:
                            deleted_data.append(
                                DeletedData(
                                    library.id,
                                    library.plex_library_name,
                                    library.emby_library_name,
                                    library.emby_library_id
                                )
                            )
                    except Exception as e:
                        self.log_error(
                            f"Check show delete keep last {utils.get_tag("error", e)}"
                        )
                elif show.action_type == "KEEP_LENGTH_DAYS":
                    try:
                        shows_deleted = self.__keep_show_days(
                            library_file_path,
                            show.action_value
                        )
                        if shows_deleted:
                            deleted_data.append(
                                DeletedData(
                                    library.id,
                                    library.plex_library_name,
                                    library.emby_library_name,
                                    library.emby_library_id
                                )
                            )
                    except Exception as e:
                        self.log_error(
                            f"Check show delete keep length {utils.get_tag("error", e)}"
                        )

        return deleted_data
    
    def __notify_plex_refresh(self, library: str):
        if library != "":
            self.plex_api.switch_plex_account_admin()
            self.plex_api.set_library_scan(library)
            return True
        return False

    def __notify_emby_refresh(self, library_id: str):
        if library_id != "":
            self.emby_api.set_library_scan(library_id)
            return True
        return False
    
    def __get_library_data(self) -> List[LibraryConfig]:
        library_list: list[LibraryConfig] = []
        for library_config in self.library_configs:
            plex_library_name = ""
            if library_config.plex_library_name != "":
                if self.plex_api.get_valid():
                    if self.plex_api.get_library(library_config.plex_library_name) != self.plex_api.get_invalid_type():
                        plex_library_name = library_config.plex_library_name
                    else:
                        self.log_warning(
                            f"{utils.get_formatted_plex()} could not find {utils.get_tag("library", library_config.plex_library_name)}"
                        )
                else:
                    self.log_warning(self.plex_api.get_connection_error_log())
            
            emby_library_name: str = ""
            emby_library_id: str = ""
            if library_config.emby_library_name != "":
                if self.emby_api.get_valid():
                    library_id = self.emby_api.get_library_id(library_config.emby_library_name)
                    if library_id != self.emby_api.get_invalid_item_id():
                        emby_library_name = library_config.emby_library_name
                        emby_library_id = library_id
                    else:
                        self.log_warning(
                            f"{utils.get_formatted_emby()} could not find {utils.get_tag("library", library_config.emby_library_name)}"
                        )
                else:
                    self.log_warning(self.emby_api.get_connection_error_log())
            
            library_list.append(
                LibraryConfig(
                    library_config.id,
                    plex_library_name,
                    emby_library_name,
                    emby_library_id,
                    library_config.utility_path,
                    library_config.shows
                )
            )
            
        return library_list
    
    def __do_maintenance(self):
        deleted_data_items: list[DeletedData] = []
        
        libraries = self.__get_library_data()
        
        for library in libraries:
            deleted_data = self.__check_library_delete_shows(library)
            for item in deleted_data:
                deleted_data_items.append(item)
        
        # Notify media servers of a refresh
        if len(deleted_data_items) > 0:
            deleted_libraries: list[DeletedData] = []
            for deleted_data in deleted_data_items:
                library_in_list: bool = False
                for deleted_library in deleted_libraries:
                    if deleted_library.library_id == deleted_data.library_id:
                        library_in_list = True
                        break
                if not library_in_list:
                    deleted_libraries.append(deleted_data)
            
            for deleted_library in deleted_libraries:
                target_name: str = ""
                if self.__notify_plex_refresh(deleted_library.plex_library_name):
                    target_name = utils.build_target_string(
                        target_name,
                        utils.get_formatted_plex(),
                        deleted_library.plex_library_name
                    )
                if self.__notify_emby_refresh(deleted_library.emby_library_id):
                    target_name = utils.build_target_string(
                        target_name,
                        utils.get_formatted_emby(),
                        deleted_library.emby_library_name
                    )

                if target_name != "":
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
