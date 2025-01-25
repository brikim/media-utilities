
import os
import shutil
from dataclasses import dataclass

from api.plex import PlexAPI
from api.emby import EmbyAPI
from common.types import CronInfo
from common.utils import get_tag, get_formatted_emby, get_formatted_plex, build_target_string
from service.ServiceBase import ServiceBase

@dataclass
class PathInfo:
    path: str
    plex_library_name: str
    emby_library_name: str
    emby_library_id: str

class FolderCleanup(ServiceBase):
    def __init__(self, ansi_code, plex_api, emby_api, config, logger, scheduler):
        super().__init__(ansi_code, self.__module__, config, logger, scheduler)
        
        self.plex_api = plex_api
        self.emby_api = emby_api
        self.paths = []
        self.ignore_folder_in_empty_check = []
        self.ignore_file_in_empty_check = []
        
        try:
            for path in config['paths_to_check']:
                plex_library_name = ''
                if 'plex_library_name' in path:
                    if self.plex_api.get_valid() == True:
                        plex_library_name = path['plex_library_name']
                    else:
                        self.log_warning('{} library defined but API not valid {} {}'.format(get_formatted_plex(), get_tag('library', path['plex_library_name']), get_tag('plex_valid', self.plex_api.get_valid())))
                
                emby_library_name = ''
                emby_library_id = ''
                if 'emby_library_name' in path:
                    if self.emby_api.get_valid() == True:
                        emby_library = self.emby_api.get_library_from_name(path['emby_library_name'])
                        if emby_library != self.emby_api.get_invalid_item_id():
                            emby_library_name = path['emby_library_name']
                            emby_library_id = emby_library['Id']
                    else:
                        self.log_warning('{} library defined but API not valid {} {}'.format(get_formatted_emby(), get_tag('library', path['emby_library_name']), get_tag('plex_valid', self.emby_api.get_valid())))
                
                self.paths.append(PathInfo(path['path'], plex_library_name, emby_library_name, emby_library_id))
                
            for folder in config['ignore_folder_in_empty_check']:
                self.ignore_folder_in_empty_check.append(folder['ignore_folder'])
        
            for file in config['ignore_file_in_empty_check']:
                self.ignore_folder_in_empty_check.append(file['ignore_file'])
            
        except Exception as e:
            self.log_error('Read config {}'.format(get_tag('error', e)))

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
                        self.log_info('Deleting empty {}'.format(get_tag('folder', dirpath)))
                        shutil.rmtree(dirpath, ignore_errors=True)
                        keep_running = True
                        folders_deleted = True
            
            if folders_deleted == True:
                deleted_paths.append(path)
        
        for deleted_path in deleted_paths:
            target_name = ''
            if deleted_path.plex_library_name != '':
                self.plex_api.switch_plex_account_admin()
                self.plex_api.set_library_scan(deleted_path.plex_library_name)
                target_name = build_target_string(target_name, get_formatted_plex(), deleted_path.plex_library_name)
            if deleted_path.emby_library_id != '':
                self.emby_api.set_library_scan(deleted_path.emby_library_id)
                target_name = build_target_string(target_name, get_formatted_emby(), deleted_path.emby_library_name)

            if target_name != '':
                self.log_info('Notified {} to refresh'.format(target_name))
    
    def init_scheduler_jobs(self):
        if self.cron is not None:
            self.log_service_enabled()
            self.scheduler.add_job(self.check_delete_empty_folders, trigger='cron', hour=self.cron.hours, minute=self.cron.minutes)
        else:
            self.log_warning('Enabled but will not Run. Cron is not valid!')
