import os
import time
from datetime import datetime, timezone
from dataclasses import dataclass

from common.types import CronInfo, UserInfo
from common.utils import get_cron_from_string, get_datetime_for_history_plex_string, get_log_ansi_code, get_tag_ansi_code, get_plex_ansi_code, get_emby_ansi_code

@dataclass
class LibraryInfo:
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
    player_name: str
    player_ansi_code: str

class DeleteWatched:
    def __init__(self, ansi_code, plex_api, tautulli_api, emby_api, jellystat_api, config, logger, scheduler):
        self.service_ansi_code = ansi_code
        self.plex_api = plex_api
        self.tautulli_api = tautulli_api
        self.emby_api = emby_api
        self.jellystat_api = jellystat_api
        self.logger = logger
        self.scheduler = scheduler
        self.cron = None
        self.user_list = []
        self.libraries = []
        self.delete_time_hours = 24
        
        try:
            self.cron = get_cron_from_string(config['cron_run_rate'], self.logger, self.__module__)
            
            for user in config['users']:
                if ('plex_name' in user and 'emby_name' in user):
                    plex_user_name = ''
                    plex_user_id = 0
                    if 'plex_name' in user:
                        plex_user_name = user['plex_name']
                        plex_user_id = self.tautulli_api.get_user_id(plex_user_name)
                    
                    emby_user_name = ''
                    emby_user_id = ''
                    if 'emby_name' in user:
                        user_id = self.emby_api.get_user_id(user['emby_name'])
                        if user_id != self.emby_api.get_invalid_item_id():
                            emby_user_name = user['emby_name']
                            emby_user_id = user_id
                        
                    
                    if plex_user_id != self.tautulli_api.get_invalid_user_id() and emby_user_id != self.emby_api.get_invalid_item_id():
                        self.user_list.append(UserInfo(plex_user_name, plex_user_id, False, emby_user_name, emby_user_id))
                    else:
                        self.logger.error('{}{}{}: No {}Plex{} user found for {} ... Skipping user'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_plex_ansi_code(), get_log_ansi_code(), plex_user_name))
                        
            for library in config['libraries']:
                plex_library_name = ''
                plex_library_id = ''
                plex_media_path = ''
                if 'plex_library_name' in library and 'plex_media_path' in library:
                    plex_library_name = library['plex_library_name']
                    plex_library_id = self.tautulli_api.get_library_id(plex_library_name)    
                    plex_media_path = library['plex_media_path']
                    
                emby_library_name = ''
                emby_library_id = ''
                emby_media_path = ''
                if 'emby_library_name' in library and 'emby_media_path' in library:
                    emby_library_name = library['emby_library_name']
                    emby_library_id = self.jellystat_api.get_library_id(emby_library_name)
                    emby_media_path = library['emby_media_path']
                
                self.libraries.append(LibraryInfo(plex_library_name, plex_library_id, plex_media_path, 
                                                    emby_library_name, emby_library_id, emby_media_path,
                                                    library['utilities_path']))

            self.delete_time_hours = config['delete_time_hours']
            
        except Exception as e:
            self.logger.error("{}{}{}: Read config {}error={}{}".format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), e))
    
    def hours_since_play(self, useUtcTime, playDateTime):
        currentDateTime = datetime.now(timezone.utc) if useUtcTime == True else datetime.now()
        time_difference = currentDateTime - playDateTime
        return (time_difference.days * 24) + (time_difference.seconds / 3600)

    def find_plex_watched_media(self, lib):
        returnFileNames = []
        try:
            dateTimeStringForHistory = get_datetime_for_history_plex_string(1)
            for user in self.user_list:
                if user.plex_user_id != 0 and lib.plex_library_id != '' and lib.plex_media_path != '':
                    watchedItems = self.tautulli_api.get_watch_history_for_user_and_library(user.plex_user_id, lib.plex_library_id, dateTimeStringForHistory)
                    for item in watchedItems:
                        if item['watched_status'] == 1:
                            fileName = self.tautulli_api.get_filename(item['rating_key'])
                            if len(fileName) > 0:
                                hoursSincePlay = self.hours_since_play(False, datetime.fromtimestamp(item['stopped']))
                                if hoursSincePlay >= self.delete_time_hours:
                                    returnFileNames.append(DeleteFileInfo(fileName.replace(lib.plex_media_path, lib.utilities_path), user.plex_user_name, 'Plex', get_plex_ansi_code()))

        except Exception as e:
            self.logger.error("{}{}{}: Find {}Plex{} watched media {}error={}{}.".format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_plex_ansi_code(), get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), e))
            
        return returnFileNames
            
    def find_emby_watched_media(self, lib):
        returnFileNames = []
        try:
            if (lib.emby_library_id != '' and lib.emby_media_path != ''):
                watchedItems = self.jellystat_api.get_library_history(lib.emby_library_id)
                for item in watchedItems:
                    for user in self.user_list:
                        if item['UserName'] == user.emby_user_name:
                            item_id = '0'
                            if 'EpisodeId' in item and item['EpisodeId'] is not None:
                                item_id = item['EpisodeId']
                            else:
                                item_id = item['NowPlayingItemId']

                            if self.emby_api.get_watched_status(user.emby_user_name, item_id) == True:
                                hoursSincePlay = self.hours_since_play(True, datetime.fromisoformat(item['ActivityDateInserted']))
                                if hoursSincePlay >= self.delete_time_hours:
                                    emby_item = self.emby_api.search_item(item_id)
                                    if emby_item is not None:
                                        returnFileNames.append(DeleteFileInfo(emby_item['Path'].replace(lib.emby_media_path, lib.utilities_path)), user.emby_user_name, 'Emby', get_emby_ansi_code())
                            break
        
        except Exception as e:
            self.logger.error("{}{}{}: Find {}Emby{} watched media {}error={}{}.".format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_emby_ansi_code(), get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), e))
            
        return returnFileNames
        
    def check_delete_media(self):
        media_to_delete = []
        
        # Find media to delete
        for lib in self.libraries:
            media_to_delete.append(self.find_plex_watched_media(lib))
            media_to_delete.append(self.find_emby_watched_media(lib))
        
        # Delete media added to the list
        number_of_deleted_media = 0
        for media_container in media_to_delete:
            for media in media_container:
                try:
                    os.remove(media.file_path)
                    self.logger.info("{}{}{}: {} watched on {}{}{} deleting {}file={}{}".format(self.service_ansi_code, self.__module__, get_log_ansi_code(), media.user_name, media.player_ansi_code, media.player_name, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), media.file_path))
                    number_of_deleted_media += 1
                except Exception as e:
                    self.logger.error("{}{}{}: Failed to delete {}file={}{} {}error={}{}".format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), media.file_path, get_tag_ansi_code(), get_log_ansi_code(), e))
                
        # If shows were deleted clean up folders and notify
        if number_of_deleted_media > 0:
            try:
                plex_lib_refreshed = False
                emby_lib_refreshed = False
                
                # Notify Plex to refresh
                self.plex_api.switch_plex_account_admin()
                for lib in self.libraries:
                    if lib.plex_library_name != '':
                        self.plex_api.set_library_scan(lib.plex_library_name)
                        plex_lib_refreshed = True
                        
                    if lib.emby_library_id != '':
                        self.emby_api.set_library_scan(lib.emby_library_id)
                        emby_lib_refreshed = True
                
                if plex_lib_refreshed == True and emby_lib_refreshed == True:
                    self.logger.info('{}{}{}: Notified {}Plex{} and {}Emby{} to refresh'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_plex_ansi_code(), get_log_ansi_code(), get_emby_ansi_code(), get_log_ansi_code()))
                elif plex_lib_refreshed == True:
                    self.logger.info('{}{}{}: Notified {}Plex{} to refresh'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_plex_ansi_code(), get_log_ansi_code()))
                elif emby_lib_refreshed == True:
                    self.logger.info('{}{}{}: Notified {}Emby{} to refresh'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_emby_ansi_code(), get_log_ansi_code()))

            except Exception as e:
                self.logger.error("{}{}{}: Clean up failed {}error={}{}.".format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), e))
        
    def init_scheduler_jobs(self):
        if self.cron is not None:
            self.logger.info('{}{}{}: Enabled. Running every {}hour={}{} {}minute={}{}'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), self.cron.hours, get_tag_ansi_code(), get_log_ansi_code(), self.cron.minutes))
            self.scheduler.add_job(self.check_delete_media, trigger='cron', hour=self.cron.hours, minute=self.cron.minutes)
        else:
            self.logger.warning('{}{}{}: Enabled but will not Run. Cron is not valid!'.format(self.service_ansi_code, self.__module__, get_log_ansi_code()))
