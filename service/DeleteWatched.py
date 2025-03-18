import os
import math
from datetime import datetime, timezone
from dataclasses import dataclass
from logging import Logger
from typing import Any, List
from apscheduler.schedulers.blocking import BlockingScheduler

from common.types import UserInfo
from common import utils

from service.ServiceBase import ServiceBase

from api.plex import PlexAPI
from api.tautulli import TautulliAPI
from api.emby import EmbyAPI
from api.jellystat import JellystatAPI

@dataclass
class UserConfigInfo:
    plex_user_name: str
    emby_user_name: str

@dataclass 
class LibraryConfigInfo:
    id: int
    plex_library_name: str
    plex_media_path: str
    emby_library_name: str
    emby_media_path: str
    utilities_path: str

@dataclass
class LibraryInfo:
    id: int
    plex_library_name: str
    plex_library_id: str
    plex_media_path: str
    emby_library_name: str
    emby_library_id: str
    emby_media_path: str
    utilities_path: str

@dataclass
class DeleteFileInfo:
    file_path: str
    user_name: str
    player: str
    library: LibraryInfo

class DeleteWatched(ServiceBase):
    def __init__(
        self, 
        ansi_code: str, 
        plex_api: PlexAPI, 
        tautulli_api: TautulliAPI, 
        emby_api: EmbyAPI, 
        jellystat_api: JellystatAPI, 
        config: Any, 
        logger: Logger, 
        scheduler: BlockingScheduler
    ):
        super().__init__(ansi_code, self.__module__, config, logger, scheduler)
        
        self.plex_api = plex_api
        self.tautulli_api = tautulli_api
        self.emby_api = emby_api
        self.jellystat_api = jellystat_api
        self.user_configs: list[UserConfigInfo] = []
        self.library_configs: list[LibraryConfigInfo] = []
        self.delete_time_hours: int = 24
        
        try:
            plex_users_defined = False
            emby_users_defined = False
            
            for user in config["users"]:
                plex_user_name: str = ""
                if "plex_name" in user:
                    plex_user_name = user["plex_name"]
                    plex_users_defined = True
                
                emby_user_name: str = ""
                if "emby_name" in user:
                    emby_user_name = user["emby_name"]
                    emby_users_defined = True
                
                if plex_user_name != "" or emby_user_name != "":
                    self.user_configs.append(
                        UserConfigInfo(plex_user_name, emby_user_name)
                    )
                else:
                    self.log_warning(
                        "No valid users found for user group ... Skipping user"
                    )
            
            current_id: int = 1      
            for library in config["libraries"]:
                plex_library_name: str = ""
                plex_media_path: str = ""
                if "plex_library_name" in library and "plex_media_path" in library:
                    if plex_users_defined:
                        plex_library_name = library["plex_library_name"]
                        plex_media_path = library["plex_media_path"]
                    else:
                        self.log_warning(
                            "{} library defined but no valid users defined {}".format(
                                utils.get_formatted_plex(),
                                utils.get_tag("library",  plex_library_name)
                            )
                        )
                    
                emby_library_name = ""
                emby_media_path = ""
                if "emby_library_name" in library and "emby_media_path" in library:
                    if emby_users_defined:
                        emby_library_name = library["emby_library_name"]
                        emby_media_path = library["emby_media_path"]
                    else:
                        self.log_warning(
                            "{} library defined but no valid users defined {}".format(
                                utils.get_formatted_emby(), 
                                utils.get_tag("library", emby_library_name)
                            )
                        )
                
                self.library_configs.append(
                    LibraryConfigInfo(
                        current_id,
                        plex_library_name,
                        plex_media_path,
                        emby_library_name,
                        emby_media_path,
                        library["utilities_path"]
                    )
                )
                current_id += 1

            if "delete_time_hours" in config:
                self.delete_time_hours = config["delete_time_hours"]
            self.get_history_days = int(math.ceil(self.delete_time_hours / 24) + 1)
        except Exception as e:
            self.log_error("Read config {}".format(utils.get_tag("error", e)))
    
    def hours_since_play(self, use_utc_time: bool, play_date_time: datetime) -> int:
        current_date_time = (
            datetime.now(timezone.utc) if use_utc_time is True else datetime.now()
        )
        time_difference = current_date_time - play_date_time
        return (time_difference.days * 24) + (time_difference.seconds / 3600)

    def __find_plex_watched_media(
        self, 
        lib: LibraryInfo, 
        user_list: List[UserInfo]
    ) -> List[DeleteFileInfo]:
        return_deletes: list[DeleteFileInfo] = []
        try:
            if lib.plex_library_name != "":
                date_time_string_for_history = utils.get_datetime_for_history_plex_string(self.get_history_days)
                for user in user_list:
                    if (
                        user.plex_user_name != "" 
                        and lib.plex_library_id != "" 
                        and lib.plex_media_path != ""
                    ):
                        watched_items = self.tautulli_api.get_watch_history_for_user_and_library(
                            user.plex_user_id, 
                            lib.plex_library_id, 
                            date_time_string_for_history
                        )
                        for item in watched_items:
                            if item["watched_status"] == 1:
                                file_name = self.tautulli_api.get_filename(item["rating_key"])
                                if len(file_name) > 0:
                                    item_hours_since_play = self.hours_since_play(
                                        False, datetime.fromtimestamp(item["stopped"])
                                    )
                                    if item_hours_since_play >= self.delete_time_hours:
                                        return_deletes.append(
                                            DeleteFileInfo(
                                                file_name.replace(
                                                    lib.plex_media_path, 
                                                    lib.utilities_path), 
                                                user.plex_friendly_name, 
                                                utils.get_formatted_plex(), 
                                                lib
                                            )
                                        )

        except Exception as e:
            self.log_error(
                "Find {} watched media {}".format(
                    utils.get_formatted_plex(), utils.get_tag("error", e)
                )
            )
            
        return return_deletes
            
    def __find_emby_watched_media(self, lib: LibraryInfo, user_list: List[UserInfo]) -> List[DeleteFileInfo]:
        return_deletes: list[DeleteFileInfo] = []
        try:
            if (lib.emby_library_name != "" 
                and lib.emby_library_id != "" 
                and lib.emby_media_path != ""
            ):
                watched_items = self.jellystat_api.get_library_history(lib.emby_library_id)
                for item in watched_items:
                    for user in user_list:
                        if user.emby_user_name != "" and item["UserName"] == user.emby_user_name:
                            item_id = "0"
                            if "EpisodeId" in item and item["EpisodeId"] is not None:
                                item_id = item["EpisodeId"]
                            else:
                                item_id = item["NowPlayingItemId"]
                            
                            emby_watched_status = self.emby_api.get_watched_status(user.emby_user_id, item_id)
                            if emby_watched_status is not None and emby_watched_status:
                                item_hours_since_play = self.hours_since_play(
                                    True, 
                                    datetime.fromisoformat(item["ActivityDateInserted"])
                                )
                                
                                if item_hours_since_play >= self.delete_time_hours:
                                    emby_item = self.emby_api.search_item(item_id)
                                    if emby_item is not None:
                                        return_deletes.append(
                                            DeleteFileInfo(
                                                emby_item["Path"].replace(
                                                    lib.emby_media_path, 
                                                    lib.utilities_path), 
                                                user.emby_user_name, 
                                                utils.get_formatted_emby(), 
                                                lib
                                            )
                                        )
                            break
        
        except Exception as e:
            self.log_error(
                "Find {} watched media {}".format(
                    utils.get_formatted_emby(), utils.get_tag("error", e))
            )
            
        return return_deletes
    
    def __get_libraries(self) -> List[LibraryInfo]:
        libraries: list[LibraryInfo] = []
        
        for library_config in self.library_configs:
            plex_library_name: str = ""
            plex_library_id: str = ""
            if library_config.plex_library_name != "":
                if self.tautulli_api.get_valid():
                    library_id = self.tautulli_api.get_library_id(library_config.plex_library_name)
                    if library_id != self.tautulli_api.get_invalid_item():
                        plex_library_name = library_config.plex_library_name
                        plex_library_id = self.tautulli_api.get_library_id(library_config.plex_library_name)
                    else:
                        self.log_warning(
                            "{} no library found for {}".format(
                                utils.get_formatted_tautulli(), 
                                utils.get_tag("library", library_config.plex_library_name)
                            )
                        )
                else:
                    self.log_warning(
                        "{} connection not currently valid".format(
                            utils.get_formatted_tautulli()
                        )
                    )
            
            emby_library_name: str = ""
            emby_library_id: str = ""
            if library_config.emby_library_name != "":
                if self.jellystat_api.get_valid():
                    library_id = self.jellystat_api.get_library_id(library_config.emby_library_name)
                    if library_id != self.jellystat_api.get_invalid_type():
                        emby_library_name = library_config.emby_library_name
                        emby_library_id = library_id
                    else:
                        self.log_warning(
                            "{} no library found for {}".format(
                                utils.get_formatted_jellystat(), 
                                utils.get_tag("library", library_config.emby_library_name)
                            )
                        )
                else:
                    self.log_warning(
                        "{} connection not currently valid".format(
                            utils.get_formatted_jellystat()
                        )
                    )
            
            libraries.append(
                LibraryInfo(
                    library_config.id, 
                    plex_library_name, 
                    plex_library_id, 
                    library_config.plex_media_path, 
                    emby_library_name, 
                    emby_library_id, 
                    library_config.emby_media_path,
                    library_config.utilities_path
                )
            )

        return libraries
    
    def __get_user_list(self) -> List[UserInfo]:
        user_list: list[UserInfo] = []
        
        for user_config in self.user_configs:
            plex_user_name: str = ""
            plex_friendly_name: str = ""
            plex_user_id: int = 0
            if user_config.plex_user_name != "":
                plex_api_valid = self.plex_api.get_valid()
                tautulli_api_valid = self.tautulli_api.get_valid()
                if plex_api_valid and tautulli_api_valid:
                    plex_user_info = self.tautulli_api.get_user_info(user_config.plex_user_name)
                    if plex_user_info != self.tautulli_api.get_invalid_item():
                        plex_user_name = user_config.plex_user_name
                        plex_user_id = plex_user_info["user_id"]
                        if (
                            "friendly_name" in plex_user_info 
                            and plex_user_info["friendly_name"] is not None 
                            and plex_user_info["friendly_name"] != ""
                        ):
                            plex_friendly_name = plex_user_info["friendly_name"]
                        else:
                            plex_friendly_name = plex_user_name
                    else:
                        self.log_warning(
                            "{} could not find {}".format(
                                utils.get_formatted_tautulli(), 
                                utils.get_tag("user", user_config.plex_user_name)
                            )
                        )
                else:
                    if not plex_api_valid:
                        self.log_warning(self.plex_api.get_connection_error_log())
                    if not tautulli_api_valid:
                        self.log_warning(self.tautulli_api.get_connection_error_log())
            
            emby_user_name = ""
            emby_user_id = ""
            if user_config.emby_user_name != "":
                emby_api_valid = self.emby_api.get_valid()
                jellystat_api_valid = self.jellystat_api.get_valid()
                if emby_api_valid and jellystat_api_valid:
                    emby_user_id = self.emby_api.get_user_id(user_config.emby_user_name)
                    if emby_user_id != self.emby_api.get_invalid_item_id():
                        emby_user_name = user_config.emby_user_name
                    else:
                        emby_user_id = ""
                        self.log_warning(
                            "{} could not find {}".format(
                                utils.get_formatted_emby(), 
                                utils.get_tag("user", user_config.emby_user_name)
                            )
                        )
                else:
                    if not emby_api_valid:
                        self.log_warning(self.emby_api.get_connection_error_log())
                    if not jellystat_api_valid:
                        self.log_warning(self.jellystat_api.get_connection_error_log())
            
            if plex_user_name != "" or emby_user_name != "":
                user_list.append(
                    UserInfo(
                        plex_user_name,
                        plex_friendly_name,
                        plex_user_id,
                        False,
                        emby_user_name,
                        emby_user_id
                    )
                )
            else:
                self.log_warning("No valid users found for user group ... Skipping user")
                    
        return user_list
        
    def __check_delete_media(self):
        media_to_delete: list[list[DeleteFileInfo]] = []
        
        # Get the current libraries to be checked by the service
        libraries = self.__get_libraries()
        user_list = self.__get_user_list()
        
        # Find media to delete
        for lib in libraries:
            media_to_delete.append(self.__find_plex_watched_media(lib, user_list))
            media_to_delete.append(self.__find_emby_watched_media(lib, user_list))
        
        # Delete media added to the list
        libraries_to_notify = []
        for media_container in media_to_delete:
            for media in media_container:
                try:
                    os.remove(media.file_path)
                    self.log_info(
                        "{} watched on {} deleting {}".format(
                            media.user_name, 
                            media.player, 
                            utils.get_tag("file", media.file_path)
                        )
                    )
                    
                    # Check if this library needs to be added to the list to notify
                    notify_lib_found = False
                    for notify_lib in libraries_to_notify:
                        if notify_lib.id == media.library.id:
                            notify_lib_found = True
                            break
                    if not notify_lib_found:
                        libraries_to_notify.append(media.library)
                except Exception as e:
                    self.log_error(
                        "Failed to delete {} {}".format(
                            utils.get_tag("file", media.file_path), 
                            utils.get_tag("error", e)
                        )
                    )
                
        # If shows were deleted clean up folders and notify
        try:
            for notify_lib in libraries_to_notify:
                target_name = ""
                if notify_lib.plex_library_name != "":
                    self.plex_api.switch_plex_account_admin()
                    self.plex_api.set_library_scan(notify_lib.plex_library_name)
                    target_name = utils.build_target_string(
                        target_name, 
                        utils.get_formatted_plex(), 
                        notify_lib.plex_library_name
                    )
                    
                if notify_lib.emby_library_id != "":
                    self.emby_api.set_library_scan(notify_lib.emby_library_id)
                    target_name = utils.build_target_string(
                        target_name, 
                        utils.get_formatted_emby(), 
                        notify_lib.emby_library_name
                    )
            
                if target_name != "":
                    self.log_info("Notified {} to refresh".format(target_name))
        
        except Exception as e:
            self.log_error("Clean up failed {}".format(utils.get_tag("error", e)))
        
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
