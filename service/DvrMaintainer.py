
import os
import glob
from datetime import datetime
from dataclasses import dataclass, field
from common.types import CronInfo
from common.utils import get_tag, get_log_ansi_code, get_tag_ansi_code, get_formatted_emby, get_formatted_plex, build_target_string
from service.ServiceBase import ServiceBase

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
    def __init__(self, ansi_code, plex_api, emby_api, config, logger, scheduler):
        super().__init__(ansi_code, self.__module__, config, logger, scheduler)
        
        self.plex_api = plex_api
        self.emby_api = emby_api
        self.libraries = []
        self.run_test = False
        current_library_id = 1
        
        try:
            library_number = 1
            for library in config['libraries']:
                plex_library_name = ''
                if 'plex_library_name' in library:
                    if self.plex_api.get_valid() == True:
                        plex_library_name = library['plex_library_name']
                    else:
                        self.log_warning('{} library defined but API not valid {} {}'.format(get_formatted_plex(), get_tag('library', library['plex_library_name']), get_tag('plex_valid', self.plex_api.get_valid())))
                
                emby_library_name = ''
                emby_library_id = ''
                if 'emby_library_name' in library:
                    if self.emby_api.get_valid() == True:
                        emby_library = self.emby_api.get_library_from_name(library['emby_library_name'])
                        if emby_library != self.emby_api.get_invalid_item_id():
                            emby_library_name = library['emby_library_name']
                            emby_library_id = emby_library['Id']
                    else:
                        self.log_warning('{} library defined but API not valid {} {}'.format(get_formatted_emby(), get_tag('library', library['emby_library_name']), get_tag('plex_valid', self.emby_api.get_valid())))
                
                # Create the library config for this library
                library_config = LibraryConfig(current_library_id, plex_library_name, emby_library_name, emby_library_id, library['utilities_path'])
                current_library_id += 1
                
                for show in library['shows']:
                    action = ''
                    action_value = 0
                    if show['action'].find('KEEP_LAST_') != -1:
                        action = 'KEEP_LAST'
                        action_value = int(show['action'].replace('KEEP_LAST_', ''))
                    elif show['action'].find('KEEP_LENGTH_DAYS_') != -1:
                        action = 'KEEP_LENGTH_DAYS'
                        action_value = int(show['action'].replace('KEEP_LENGTH_DAYS_', ''))
                    
                    if action != '': 
                        library_config.shows.append(ShowConfig(show['name'], action, action_value))
                    else:
                        self.log_error('Unknown show action {} ... Skipping'.format(show['action']))
                        
                if len(library_config.shows) > 0:
                    self.libraries.append(library_config)
                else:
                    self.log_error('Library {} has no valid shows ... Skipping'.format(library_number))
                    
                library_number += 1

        except Exception as e:
            self.log_error('Read config {}'.format(get_tag('error', e)))
    
    def get_files_in_path(self, path):
        file_info = []
        for file in glob.glob(path + "/**/*", recursive=True):
            if file.endswith(".ts") or file.endswith(".mkv"):
                file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(file))
                file_info.append(FileInfo(file, file_age.days + (file_age.seconds / 86400)))
        return file_info

    def delete_file(self, pathFileName):
        if self.run_test == True:
            self.log_info('Running test! Would delete {}'.format(get_tag('file', pathFileName)))
        else:
            try:
                os.remove(pathFileName)
            except Exception as e:
                self.log_error('Problem deleting {} {}'.format(get_tag('file', pathFileName), get_tag('error', e)))
    
    def keep_last_delete(self, path, keep_last):
        shows_deleted = False
        file_info = self.get_files_in_path(path)
        if len(file_info) > keep_last:
            self.log_info('KEEP_LAST_{} {} {}'.format(keep_last, get_tag('episodes', len(file_info)), get_tag('path', path)))
            try:
                sorted_file_info = sorted(file_info, key=lambda item: item.age_days, reverse=True)
                shows_to_delete = len(file_info) - keep_last
                deleted_shows = 0
                for file in sorted_file_info:
                    self.log_info('KEEP_LAST_{} deleting oldest {}age days={}{:.1f} {}'.format(keep_last, get_tag_ansi_code(), get_log_ansi_code(), file.age_days, get_tag('file', file.path)))
                    self.delete_file(file.path)
                    shows_deleted = True

                    deleted_shows += 1
                    if deleted_shows >= shows_to_delete:
                        break
            
            except Exception as e:
                self.log_error('KEEP_LAST_{} error sorting files {}'.format(keep_last, get_tag('error', e)))

        return shows_deleted

    def keep_show_days(self, path, keep_days):
        shows_deleted = False
        file_info = self.get_files_in_path(path)
        for file in file_info:
            if file.age_days >= keep_days:
                self.log_info('KEEP_DAYS_{} deleting {}age days={}{:.1f} {}'.format(keep_days,  get_tag_ansi_code(), get_log_ansi_code(), file.age_days, get_tag('file', file.path)))
                self.delete_file(file.path)
                shows_deleted = True
        return shows_deleted

    def check_library_delete_shows(self, library):
        deleted_data = []
        for show in library.shows:
            library_file_path = library.utility_path + '/' + show.name
            if os.path.exists(library_file_path) == True:
                if show.action_type == 'KEEP_LAST':
                    try:
                        shows_deleted = self.keep_last_delete(library_file_path, show.action_value)
                        if shows_deleted == True:
                            deleted_data.append(DeletedData(library.id, library.plex_library_name, library.emby_library_name, library.emby_library_id))
                    except Exception as e:
                        self.log_error('Check show delete keep last {}'.format(get_tag('error', e)))
                elif show.action_type == 'KEEP_LENGTH_DAYS':
                    try:
                        shows_deleted = self.keep_show_days(library_file_path, show.action_value)
                        if shows_deleted == True:
                            deleted_data.append(DeletedData(library.id, library.plex_library_name, library.emby_library_name, library.emby_library_id))
                    except Exception as e:
                        self.log_error('Check show delete keep length {}'.format(get_tag('error', e)))

        return deleted_data
    
    def notify_plex_refresh(self, library):
        if library != '':
            self.plex_api.switch_plex_account_admin()
            self.plex_api.set_library_scan(library)
            return True
        return False

    def notify_emby_refresh(self, library_id):
        if library_id != '':
            self.emby_api.set_library_scan(library_id)
            return True
        return False
        
    def do_maintenance(self):
        deleted_data_items = []
        
        for library in self.libraries:
            deleted_data = self.check_library_delete_shows(library)
            for item in deleted_data:
                deleted_data_items.append(item)
        
        # Notify media servers of a refresh
        if len(deleted_data_items) > 0:
            deleted_libraries = []
            for deleted_data in deleted_data_items:
                library_in_list = False
                for deleted_library in deleted_libraries:
                    if deleted_library.library_id == deleted_data.library_id:
                        library_in_list = True
                        break
                if library_in_list == False:
                    deleted_libraries.append(deleted_data)
            
            for deleted_library in deleted_libraries:
                target_name = ''
                if self.notify_plex_refresh(deleted_library.plex_library_name) == True:
                    target_name = build_target_string(target_name, get_formatted_plex(), deleted_library.plex_library_name)
                if self.notify_emby_refresh(deleted_library.emby_library_id) == True:
                    target_name = build_target_string(target_name, get_formatted_emby(), deleted_library.emby_library_name)

                if target_name != '':
                    self.log_info('Notified {} to refresh'.format(target_name))
    
    def init_scheduler_jobs(self):
        if self.cron is not None:
            self.log_service_enabled()
            self.scheduler.add_job(self.do_maintenance, trigger='cron', hour=self.cron.hours, minute=self.cron.minutes)
        else:
            self.log_warning('Enabled but will not Run. Cron is not valid!')
