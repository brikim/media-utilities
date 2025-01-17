
import os
import glob
from datetime import datetime
from dataclasses import dataclass
from common.types import CronInfo
from common.utils import get_log_ansi_code, get_tag_ansi_code
from service.ServiceBase import ServiceBase

@dataclass
class ShowConfig:
    name: str
    action_type: str
    action_value: int
    plex_library_name: str
    emby_library_id: str
    utility_path: str

@dataclass
class DeletedData:
    plex_library_name: str
    emby_library_id: str
@dataclass
class FileInfo:
    path: str
    age_days: float

class DvrMaintainer(ServiceBase):
    def __init__(self, ansi_code, plex_api, emby_api, config, logger, scheduler):
        super().__init__(ansi_code, self.__module__, config, logger, scheduler)
        
        self.plex_api = plex_api
        self.emby_api = emby_api
        self.show_configurations = []
        self.run_test = False
        
        try:
            for show in config['show_details']:
                action = ''
                actionValue = 0
                if show['action'].find('KEEP_LAST_') != -1:
                    action = 'KEEP_LAST'
                    actionValue = int(show['action'].replace('KEEP_LAST_', ''))
                elif show['action'].find('KEEP_LENGTH_DAYS_') != -1:
                    action = 'KEEP_LENGTH_DAYS'
                    actionValue = int(show['action'].replace('KEEP_LENGTH_DAYS_', ''))
                
                show_plex_library_name = ''
                if 'plex_library_name' in show:
                    if self.plex_api.get_valid() == True:
                        show_plex_library_name = show['plex_library_name']
                    else:
                        self.log_warning('{} library defined but API not valid {} {}'.format(self.formatted_plex, self.get_tag('library', show['plex_library_name']), self.get_tag('plex_valid', self.plex_api.get_valid())))
                    
                show_emby_library_id = ''
                if 'emby_library_name' in show:
                    if self.emby_api.get_valid() == True:
                        emby_library = self.emby_api.get_library_from_name(show['emby_library_name'])
                        if emby_library != '':
                            show_emby_library_id = emby_library['Id']
                    else:
                        self.log_warning('{} library defined but API not valid {} {}'.format(self.formatted_emby, self.get_tag('library', show['emby_library_name']), self.get_tag('plex_valid', self.emby_api.get_valid())))
                    
                if action != '':
                    self.show_configurations.append(ShowConfig(show['name'], action, actionValue, show_plex_library_name, show_emby_library_id, show['utilities_path'].rstrip('/')))
                else:
                    self.log_error('Unknown show action {}. Skipping show detail'.format(show['action']))
        
        except Exception as e:
            self.log_error('Read config {}'.format(self.get_tag('error', e)))
    
    def get_files_in_path(self, path):
        fileInfo = []
        for file in glob.glob(path + "/**/*", recursive=True):
            if file.endswith(".ts") or file.endswith(".mkv"):
                fileAge = datetime.now() - datetime.fromtimestamp(os.path.getmtime(file))
                fileInfo.append(FileInfo(file, fileAge.days + (fileAge.seconds / 86400)))
        return fileInfo

    def delete_file(self, pathFileName):
        if self.run_test == True:
            self.log_info('Running test! Would delete {}'.format(self.get_tag('file', pathFileName)))
        else:
            try:
                os.remove(pathFileName)
            except Exception as e:
                self.log_error('Problem deleting {} {}'.format(self.get_tag('file', pathFileName), self.get_tag('error', e)))
    
    def keep_last_delete(self, path, keep_last):
        showsDeleted = False
        fileInfo = self.get_files_in_path(path)
        if len(fileInfo) > keep_last:
            self.log_info('KEEP_LAST_{} {} {}'.format(keep_last, self.get_tag('episodes', len(fileInfo)), self.get_tag('path', path)))
            try:
                sortedFileInfo = sorted(fileInfo, key=lambda item: item.age_days, reverse=True)

                showsToDelete = len(fileInfo) - keep_last
                deletedShows = 0
                for file in sortedFileInfo:
                    self.log_info('KEEP_LAST_{} deleting oldest {}age days={}{:.1f} {}'.format(keep_last, get_tag_ansi_code(), get_log_ansi_code(), file.age_days, self.get_tag('file', file.path)))
                    self.delete_file(file.path)
                    showsDeleted = True

                    deletedShows += 1
                    if deletedShows >= showsToDelete:
                        break
            
            except Exception as e:
                self.log_error('KEEP_LAST_{} error sorting files {}'.format(keep_last, self.get_tag('error', e)))

        return showsDeleted

    def keep_show_days(self, path, keep_days):
        showsDeleted = False
        fileInfo = self.get_files_in_path(path)
        for file in fileInfo:
            if file.age_days >= keep_days:
                self.log_info('KEEP_DAYS_{} deleting {}age days={}{:.1f} {}'.format(keep_days,  get_tag_ansi_code(), get_log_ansi_code(), file.age_days, self.get_tag('file', file.path)))
                self.delete_file(file.path)
                showsDeleted = True
        return showsDeleted

    def check_show_delete(self, config):
        deleted_data = []
        libraryFilePath = config.utility_path + '/' + config.name
        if os.path.exists(libraryFilePath) == True:
            if config.action_type == 'KEEP_LAST':
                try:
                    showsDeleted = self.keep_last_delete(libraryFilePath, config.action_value)
                    if showsDeleted == True:
                        deleted_data.append(DeletedData(config.plex_library_name, config.emby_library_id))
                except Exception as e:
                    self.log_error('Check show delete keep last {}'.format(self.get_tag('error', e)))
            elif config.action_type == 'KEEP_LENGTH_DAYS':
                try:
                    showsDeleted = self.keep_show_days(libraryFilePath, config.action_value)
                    if showsDeleted == True:
                        deleted_data.append(DeletedData(config.plex_library_name, config.emby_library_id))
                except Exception as e:
                    self.log_error('Check show delete keep length {}'.format(self.get_tag('error', e)))

        return deleted_data
    
    def notify_plex_refresh(self, library_list):
        library_refreshed = False
        self.plex_api.switch_plex_account_admin()
        for library in library_list:
            if library != '':
                self.plex_api.set_library_scan(library)
                library_refreshed = True
        return library_refreshed

    def notify_emby_refresh(self, library_ids):
        library_refreshed = False
        for id in library_ids:
            if id != '':
                self.emby_api.set_library_scan(id)
                library_refreshed = True
        return library_refreshed
        
    def do_maintenance(self):
        deleted_data_items = []
        
        for show_config in self.show_configurations:
            deleted_data = self.check_show_delete(show_config)
            for item in deleted_data:
                deleted_data_items.append(item)
        
        # Notify media servers of a refresh
        if len(deleted_data_items) > 0:
            plex_libraries = []
            emby_library_ids = []
            for deleted_data in deleted_data_items:
                plex_libraries.append(deleted_data.plex_library_name)
                emby_library_ids.append(deleted_data.emby_library_id)
                
            plex_lib_refreshed = self.notify_plex_refresh(list(set(plex_libraries)))
            emby_lib_refreshed = self.notify_emby_refresh(list(set(emby_library_ids)))
            
            if plex_lib_refreshed == True and emby_lib_refreshed == True:
                self.log_info('Notified {} and {} to refresh'.format(self.formatted_plex, self.formatted_emby))
            elif plex_lib_refreshed == True:
                self.log_info('Notified {} to refresh'.format(self.formatted_plex))
            elif emby_lib_refreshed == True:
                self.log_info('Notified {} to refresh'.format(self.formatted_emby))
    
    def init_scheduler_jobs(self):
        if self.cron is not None:
            self.log_service_enabled()
            self.scheduler.add_job(self.do_maintenance, trigger='cron', hour=self.cron.hours, minute=self.cron.minutes)
        else:
            self.log_warning('Enabled but will not Run. Cron is not valid!')
