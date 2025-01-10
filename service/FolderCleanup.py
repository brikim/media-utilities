
import os
import shutil
import time
from dataclasses import dataclass

from api.plex import PlexAPI
from api.emby import EmbyAPI
from common.types import CronInfo
from common.utils import get_cron_from_string, get_log_ansi_code, get_tag_ansi_code, get_plex_ansi_code

@dataclass
class PathInfo:
    path: str
    plex_library: str

class FolderCleanup:
    def __init__(self, ansi_code, plex_api, emby_api, config, logger, scheduler):
        self.service_ansi_code = ansi_code
        self.plex_api = plex_api
        self.emby_api = emby_api
        self.logger = logger
        self.scheduler = scheduler
        self.cron = None
        self.notify_plex_of_delete = False
        self.notify_emby_of_delete = False
        self.paths = []
        self.ignore_folder_in_empty_check = []
        self.ignore_file_in_empty_check = []
        
        try:
            self.cron = get_cron_from_string(config['cron_run_rate'], self.logger, self.__module__)
            
            if 'notify_plex_of_delete' in config:
                self.notify_plex_to_refresh = config['notify_plex_of_delete'] == 'True'
            
            if 'notify_emby_of_delete' in config:
                self.notify_emby_of_delete = config['notify_emby_of_delete'] == 'True'
            
            for path in config['paths_to_check']:
                plex_library = ''
                if 'plex_library' in path:
                    plex_library = path['plex_library']
                else:
                    if self.notify_plex_of_delete == True:
                        self.logger.warning('{}{}{}: Set to notify {}plex{} to delete but path {} has no plex library defined!'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_plex_ansi_code(), get_log_ansi_code(), path['path']))
                self.paths.append(PathInfo(path['path'], plex_library))
                
            for folder in config['ignore_folder_in_empty_check']:
                self.ignore_folder_in_empty_check.append(folder['ignore_folder'])
        
            for file in config['ignore_file_in_empty_check']:
                self.ignore_folder_in_empty_check.append(file['ignore_file'])
            
        except Exception as e:
            self.logger.error('{}{}{}: Read config {}error={}{}'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), e))

    def is_dir_empty(self, dirnames):
        dir_empty = True
        for dirname in dirnames:
            if len(self.ignore_folder_in_empty_check) > 0:
                for ignore_dir in self.ignore_folder_in_empty_check:
                    if dirname != ignore_dir:
                        dir_empty = False
                        break
            else:
                dir_empty = False
                
            if dir_empty == False:
                break
        return dir_empty
    
    def is_files_empty(self, filenames):
        filenames_empty = True
        for filename in filenames:
            if len(self.ignore_file_in_empty_check) > 0:
                for ignore_file in self.ignore_file_in_empty_check:
                    if filename != ignore_file:
                        filenames_empty = False
                        break
            else:
                filenames_empty = False
            
            if filenames_empty == False:
                break
        return filenames_empty
    
    def check_delete_empty_folders(self):
        deleted_paths = []
        for path in self.paths:
            folders_deleted = False
            
            keep_running = True
            while keep_running == True:
                keep_running = False
                for dirpath, dirnames, filenames in os.walk(path.path, topdown=False):
                    if self.is_dir_empty(dirnames) == True and self.is_files_empty(filenames) == True:
                        self.logger.info('{}{}{}: Deleting empty {}folder={}{}'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), dirpath))
                        shutil.rmtree(dirpath, ignore_errors=True)
                        keep_running = True
                        folders_deleted = True
            
            if folders_deleted == True:
                deleted_paths.append(path)
        
        notified_media_servers = False
        for deleted_path in deleted_paths:
            if self.notify_plex_of_delete == True and deleted_path.plex_library != '':
                self.plex_api.switch_plex_account_admin()
                self.plex_api.set_library_scan(deleted_path.plex_library)
                notified_media_servers = True
            
            if self.notify_emby_of_delete == True:
                self.emby_api.set_library_scan()
                notified_media_servers = True
        
        if notified_media_servers == True:
                self.logger.info('{}{}{}: Notifying Media Servers to refresh'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(),))
    
    def init_scheduler_jobs(self):
        if self.cron is not None:
            self.logger.info('{}{}{}: Enabled. Running every {}hour={}{} {}minute={}{}'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), get_tag_ansi_code(), get_log_ansi_code(), self.cron.hours, get_tag_ansi_code(), get_log_ansi_code(), self.cron.minutes))
            self.scheduler.add_job(self.check_delete_empty_folders, trigger='cron', hour=self.cron.hours, minute=self.cron.minutes)
        else:
            self.logger.warning('{}{}{}: Enabled but will not Run. Cron is not valid!'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(),))
