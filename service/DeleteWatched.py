import os
from datetime import datetime, timezone
from dataclasses import dataclass

from common.user_stats import UserInfo
from common.utils import delete_empty_folders, get_datetime_for_history_plex_string

@dataclass
class LibraryInfo:
    plex_library_name: str
    plex_library_id: str
    plex_media_path: str
    emby_library_name: str
    emby_library_id: str
    emby_media_path: str
    utilities_path: str

class DeleteWatched:
    def __init__(self, plex_api, tautulli_api, emby_api, jellystat_api, config, logger, scheduler):
        self.plex_api = plex_api
        self.tautulli_api = tautulli_api
        self.emby_api = emby_api
        self.jellystat_api = jellystat_api
        self.logger = logger
        self.scheduler = scheduler
        self.user_list = []
        self.libraries = []
        self.cronHours = ''
        self.cronMinutes = ''
        self.delete_time_hours = 24
        self.log_pending_delete_time_hours = 0
        
        try:
            cronParams = config['cron_run_rate'].split()
            if len(cronParams) >= 2 and len(cronParams) <= 5:
                self.cronMinutes = cronParams[0]
                self.cronHours = cronParams[1]
            else:
                self.logger.error('{}: Invalid Cron Expression {}'.format(self.__module__, config['cron_run_rate']))
            
            for user in config['users']:
                if ('plexName' in user and 'embyName' in user):
                    plexUserName = user['plexName']
                    embyUserName = user['embyName']
                    plexUserId = self.tautulli_api.get_user_id(plexUserName)
                    embyUserId = self.emby_api.get_user_id(embyUserName)
                    if plexUserId != 0 and embyUserId != '0':
                        self.user_list.append(UserInfo(plexUserName, plexUserId, embyUserName, embyUserId))
                    else:
                        self.logger.error('{}: No Plex user found for {} ... Skipping User'.format(self.__module__ , plexUserName))
                        
            for library in config['libraries']:
                plexLibraryName = library['plexLibraryName']
                embyLibraryName = library['embyLibraryName']
                plexLibraryId = self.tautulli_api.get_library_id(plexLibraryName)
                embyLibraryId = self.jellystat_api.get_library_id(embyLibraryName)
                self.libraries.append(LibraryInfo(plexLibraryName, plexLibraryId, library['plexMediaPath'], 
                                                    embyLibraryName, embyLibraryId, library['embyMediaPath'],
                                                    library['utilitiesPath']))

            self.delete_time_hours = config['delete_time_hours']
            self.log_pending_delete_time_hours = self.delete_time_hours * 0.7
            
        except Exception as e:
            self.logger.error("{}: Read config ERROR:{}".format(self.__module__ , e))
    
    def hours_since_play(self, useUtcTime, playDateTime):
        currentDateTime = datetime.now(timezone.utc) if useUtcTime == True else datetime.now()
        time_difference = currentDateTime - playDateTime
        return (time_difference.days * 24) + (time_difference.seconds / 3600)

    def find_plex_watched_media(self, lib):
        try:
            returnFileNames = []
            dateTimeStringForHistory = get_datetime_for_history_plex_string(1)
            for user in self.user_list:
                watchedItems = self.tautulli_api.get_watch_history_for_user_and_library(user.plex_user_id, lib.plex_library_id, dateTimeStringForHistory)
                for item in watchedItems:
                    if item['watched_status'] == 1:
                        fileName = self.tautulli_api.get_filename(item['rating_key'])
                        if len(fileName) > 0:
                            hoursSincePlay = self.hours_since_play(False, datetime.fromtimestamp(item['stopped']))
                            if hoursSincePlay >= self.delete_time_hours:
                                returnFileNames.append(fileName.replace(lib.plex_media_path, lib.utilities_path))
                            else:
                                if hoursSincePlay >= self.log_pending_delete_time_hours:
                                    self.logger.info("{}: Pending Delete. Plex watched {:.1f} hours ago will delete at {} hours. {}".format(self.__module__, hoursSincePlay, self.delete_time_hours, fileName))

            return returnFileNames

        except Exception as e:
            self.logger.error("{}: Find Plex Watched Media ERROR: {}.".format(self.__module__, e))
            
    def find_emby_watched_media(self, lib):
        returnFileNames = []
        try:
            watchedItems = self.jellystat_api.get_library_history(lib.emby_library_id)
            for item in watchedItems:
                for user in self.user_list:
                    if item['UserName'] == user.emby_user_name:
                        if self.emby_api.get_watched_status(user.emby_user_name, item['NowPlayingItemId']) == True:
                            hoursSincePlay = self.hours_since_play(True, datetime.fromisoformat(item['ActivityDateInserted']))
                            if hoursSincePlay >= self.delete_time_hours:
                                itemDetails = self.jellystat_api.get_item_details(item['NowPlayingItemId'])
                                for item in itemDetails:
                                    fileName = item['Path']
                                    returnFileNames.append(fileName.replace(lib.emby_media_path, lib.utilities_path))
                            else:
                                if hoursSincePlay >= self.log_pending_delete_time_hours:
                                    self.logger.info("{}: Pending Delete. Emby watched {:.1f} hours ago will delete at {} hours. {}".format(self.__module__, hoursSincePlay, self.delete_time_hours, fileName))
        except Exception as e:
            self.logger.error("{}: Find Emby Watched Media ERROR: {}.".format(self.__module__, e))
            
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
                os.remove(media)
                self.logger.info("{}: Deleted File: {}".format(self.__module__, media))
                number_of_deleted_media += 1
                
        # If shows were deleted clean up folders and notify
        if number_of_deleted_media > 0:
            try:
                # Clean up empty folders in paths
                checkEmptyFolderPaths = []
                for lib in self.libraries:
                    checkEmptyFolderPaths.append(lib.utilities_path)
                delete_empty_folders(checkEmptyFolderPaths, self.logger, self.__module__)

                # Notify Plex to refresh
                self.plex_api.switch_plex_account_admin()
                for lib in self.libraries:
                    self.plex_api.set_library_refresh(lib.plex_library_name)
                
                # Notify Emby to refresh
                self.emby_api.set_library_refresh()
                
                self.logger.info("{}: Notifying Media Servers to Refresh".format(self.__module__))
            except Exception as e:
                self.logger.error("{}: Clean up failed ERROR: {}.".format(self.__module__, e))
        
    def init_scheduler_jobs(self):
        self.logger.info('{} Enabled. Running every hour:{} minute:{}'.format(self.__module__, self.cronHours, self.cronMinutes))
        self.scheduler.add_job(self.check_delete_media, trigger='cron', hour=self.cronHours, minute=self.cronMinutes)
