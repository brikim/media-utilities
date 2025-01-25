import os
from datetime import datetime, timezone
from dataclasses import dataclass

from common.types import CronInfo, UserInfo
from common.utils import get_datetime_for_history_plex_string, get_tag, get_formatted_emby, get_formatted_plex
from service.ServiceBase import ServiceBase

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
    player: str

class DeleteWatched(ServiceBase):
    def __init__(self, ansi_code, plex_api, tautulli_api, emby_api, jellystat_api, config, logger, scheduler):
        super().__init__(ansi_code, self.__module__, config, logger, scheduler)
        
        self.plex_api = plex_api
        self.tautulli_api = tautulli_api
        self.emby_api = emby_api
        self.jellystat_api = jellystat_api
        self.user_list = []
        self.libraries = []
        self.delete_time_hours = 24
        
        try:
            plex_users_defined = False
            emby_users_defined = False
            
            for user in config['users']:
                plex_user_name = ''
                plex_friendly_name = ''
                plex_user_id = 0
                if 'plex_name' in user:
                    if self.plex_api.get_valid() == True and self.tautulli_api.get_valid() == True:
                        plex_user_name = user['plex_name']
                        plex_user_info = self.tautulli_api.get_user_info(plex_user_name)
                        if plex_user_info != self.tautulli_api.get_invalid_item():
                            plex_user_id = plex_user_info['user_id']
                            if 'friendly_name' in plex_user_info and plex_user_info['friendly_name'] is not None and plex_user_info['friendly_name'] != '':
                                plex_friendly_name = plex_user_info['friendly_name']
                            else:
                                plex_friendly_name = plex_user_name
                            plex_users_defined = True                            
                        else:
                            plex_user_name = ''
                            
                    else:
                        self.log_warning('{} user defined but API not valid {} {} {}'.format(get_formatted_plex(), get_tag('user', user['plex_name']), get_tag('plex_valid', self.plex_api.get_valid()), get_tag('tautulli_valid', self.tautulli_api.get_valid())))
                
                emby_user_name = ''
                emby_user_id = ''
                if 'emby_name' in user:
                    if self.emby_api.get_valid() == True and self.jellystat_api.get_valid() == True:
                        emby_user_name = user['emby_name']
                        emby_user_id = self.emby_api.get_user_id(emby_user_name)
                        if emby_user_id == self.emby_api.get_invalid_item_id():
                            emby_user_name = ''
                        else:
                            emby_users_defined = True
                    else:
                        self.log_warning('{} user defined but API not valid {} {} {}'.format(get_formatted_emby(), get_tag('user', user['emby_name']), get_tag('emby_valid', self.emby_api.get_valid()), get_tag('jellystat_valid', self.jellystat_api.get_valid())))
                    
                if plex_user_name != '' or emby_user_name != '':    
                    self.user_list.append(UserInfo(plex_user_name, plex_friendly_name, plex_user_id, False, emby_user_name, emby_user_id))
                else:
                    self.log_warning('No valid users found for user group ... Skipping user')
                        
            for library in config['libraries']:
                plex_library_name = ''
                plex_library_id = ''
                plex_media_path = ''
                if 'plex_library_name' in library and 'plex_media_path' in library:
                    if plex_users_defined == True:
                        plex_library_name = library['plex_library_name']
                        plex_library_id = self.tautulli_api.get_library_id(plex_library_name)    
                        plex_media_path = library['plex_media_path']
                    else:
                        self.log_warning('{} library defined but no valid users defined {}'.format(get_formatted_plex(), get_tag('library',  plex_library_name)))
                    
                emby_library_name = ''
                emby_library_id = ''
                emby_media_path = ''
                if 'emby_library_name' in library and 'emby_media_path' in library:
                    if emby_users_defined == True:
                        emby_library_name = library['emby_library_name']
                        emby_library_id = self.jellystat_api.get_library_id(emby_library_name)
                        emby_media_path = library['emby_media_path']
                    else:
                        self.log_warning('{} library defined but no valid users defined {}'.format(get_formatted_emby(), get_tag('library', emby_library_name)))
                
                self.libraries.append(LibraryInfo(plex_library_name, plex_library_id, plex_media_path, 
                                                    emby_library_name, emby_library_id, emby_media_path,
                                                    library['utilities_path']))

            self.delete_time_hours = config['delete_time_hours']
            
        except Exception as e:
            self.log_error('Read config {}'.format(get_tag('error', e)))
    
    def hours_since_play(self, useUtcTime, playDateTime):
        currentDateTime = datetime.now(timezone.utc) if useUtcTime == True else datetime.now()
        time_difference = currentDateTime - playDateTime
        return (time_difference.days * 24) + (time_difference.seconds / 3600)

    def find_plex_watched_media(self, lib):
        returnFileNames = []
        try:
            if lib.plex_library_name != '':
                dateTimeStringForHistory = get_datetime_for_history_plex_string(1)
                for user in self.user_list:
                    if user.plex_user_name != '' and lib.plex_library_id != '' and lib.plex_media_path != '':
                        watchedItems = self.tautulli_api.get_watch_history_for_user_and_library(user.plex_user_id, lib.plex_library_id, dateTimeStringForHistory)
                        for item in watchedItems:
                            if item['watched_status'] == 1:
                                fileName = self.tautulli_api.get_filename(item['rating_key'])
                                if len(fileName) > 0:
                                    hoursSincePlay = self.hours_since_play(False, datetime.fromtimestamp(item['stopped']))
                                    if hoursSincePlay >= self.delete_time_hours:
                                        returnFileNames.append(DeleteFileInfo(fileName.replace(lib.plex_media_path, lib.utilities_path), user.plex_friendly_name, get_formatted_plex()))

        except Exception as e:
            self.log_error('Find {} watched media {}'.format(get_formatted_plex(), get_tag('error', e)))
            
        return returnFileNames
            
    def find_emby_watched_media(self, lib):
        returnFileNames = []
        try:
            if (lib.emby_library_name != '' and lib.emby_library_id != '' and lib.emby_media_path != ''):
                watchedItems = self.jellystat_api.get_library_history(lib.emby_library_id)
                for item in watchedItems:
                    for user in self.user_list:
                        if user.emby_user_name != '' and item['UserName'] == user.emby_user_name:
                            item_id = '0'
                            if 'EpisodeId' in item and item['EpisodeId'] is not None:
                                item_id = item['EpisodeId']
                            else:
                                item_id = item['NowPlayingItemId']
                            if self.emby_api.get_watched_status(user.emby_user_id, item_id) == True:
                                hoursSincePlay = self.hours_since_play(True, datetime.fromisoformat(item['ActivityDateInserted']))
                                if hoursSincePlay >= self.delete_time_hours:
                                    emby_item = self.emby_api.search_item(item_id)
                                    if emby_item is not None:
                                        returnFileNames.append(DeleteFileInfo(emby_item['Path'].replace(lib.emby_media_path, lib.utilities_path), user.emby_user_name, get_formatted_emby()))
                            break
        
        except Exception as e:
            self.log_error('Find {} watched media {}'.format(get_formatted_emby(), get_tag('error', e)))
            
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
                    self.log_info('{} watched on {} deleting {}'.format(media.user_name, media.player, get_tag('file', media.file_path)))
                    number_of_deleted_media += 1
                except Exception as e:
                    self.log_error('Failed to delete {} {}'.format(get_tag('file', media.file_path), get_tag('error', e)))
                
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
                    self.log_info('Notified {} and {} to refresh'.format(get_formatted_plex(), get_formatted_emby()))
                elif plex_lib_refreshed == True:
                    self.log_info('Notified {} to refresh'.format(get_formatted_plex()))
                elif emby_lib_refreshed == True:
                    self.log_info('Notified {} to refresh'.format(get_formatted_emby()))

            except Exception as e:
                self.log_error('Clean up failed {}'.format(get_tag('error', e)))
        
    def init_scheduler_jobs(self):
        if self.cron is not None:
            self.log_service_enabled()
            self.scheduler.add_job(self.check_delete_media, trigger='cron', hour=self.cron.hours, minute=self.cron.minutes)
        else:
            self.log_warning('Enabled but will not Run. Cron is not valid!')
