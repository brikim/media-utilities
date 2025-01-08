
import os
import time
from datetime import datetime
import threading
from threading import Thread
from dataclasses import dataclass
import inotify.adapters
import inotify.constants

from api.plex import PlexAPI
from api.emby import EmbyAPI
from common.utils import get_log_ansi_code

@dataclass
class ScanInfo:
    name: str
    path: str
    plex_library_valid: bool
    plex_library: str
    emby_library_valid: bool
    emby_library: str
    time: float
    
@dataclass
class CheckPathData:
    path: str
    i: inotify.adapters.Inotify
    scan_mask: int
    time: float
    deleted: bool
    
class AutoScan:
    def __init__(self, plex_api, emby_api, config, logger):
        self.service_ansi_code = '\33[96m'
        self.tag_ansi_code = '\33[36m'
        self.plex_api = plex_api
        self.emby_api = emby_api
        self.logger = logger
        self.ignore_folder_with_name = []
        self.valid_file_extensions = []
        
        self.sleep_time = 1
        
        self.seconds_before_notify = 0
        self.seconds_between_notifies = 0
        self.last_notify_time = 0.0
        
        self.notify_plex = False
        self.notify_emby = False
        
        self.scans = []
        
        self.monitors = []
        self.monitor_lock = threading.Lock()
        self.monitor_thread = None
        
        self.watched_paths_lock = threading.Lock()
        self.watched_paths = []
        
        self.threads = []
        self.stop_threads = False
        
        self.lock_check_new_paths = threading.Lock()
        self.check_new_paths = []
        
        try:
            self.seconds_before_notify = max(config['seconds_before_notify'], 30)
            self.seconds_between_notifies = max(config['seconds_between_notifies'], 10)
            
            if 'notify_plex' in config:
                self.notify_plex = config['notify_plex'] == 'True'
            
            if 'notify_emby' in config:
                self.notify_emby = config['notify_emby'] == 'True'
            
            for scan in config['scans']:
                plex_library = ''
                if self.notify_plex == True and 'plex_path' in scan:
                    plex_library = self.plex_api.get_library_name_from_path(scan['plex_path'])
                
                emby_library = ''
                if self.notify_emby == True and 'emby_path' in scan:
                    emby_library = self.emby_api.get_library_name_from_path(scan['emby_path'])
                
                self.scans.append(ScanInfo(scan['name'], scan['container_path'], plex_library != '', plex_library, emby_library != '', emby_library, 0.0))
            
            for folder in config['ignore_folder_with_name']:
                self.ignore_folder_with_name.append(folder['ignore_folder'])
                
            if config['valid_file_extensions'] != '':
                self.valid_file_extensions = config['valid_file_extensions'].split(',')
                
                
        except Exception as e:
            self.logger.error('{}{}{}: Read config ERROR:{}'.format(self.service_ansi_code, self.__module__, get_log_ansi_code() , e))
    
    def shutdown(self):
        self.stop_threads = True
        
        # Create a temp file to notify the inotify adapters
        for scan in self.scans:
            temp_file = scan.path + '/temp.txt'
            with open(temp_file, 'w') as file:
                file.write('BREAK')
            
        # allow time for the events
        time.sleep(1)
        
        with self.monitor_lock:
            self.monitors.clear()
                            
        # clean up the temp files
        for scan in self.scans:
            temp_file = scan.path + '/temp.txt'
            os.remove(temp_file)
        
        self.logger.info('{}{}{}: Successful shutdown'.format(self.service_ansi_code, self.__module__, get_log_ansi_code()))
    
    def _log_moved_to_target(self, name, library, server_name):
        self.logger.info('{}{}{}: Monitor moved to target {}name={}{} {}target={}{} {}library={}{}'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), self.tag_ansi_code, get_log_ansi_code(), name, self.tag_ansi_code, get_log_ansi_code(), server_name, self.tag_ansi_code, get_log_ansi_code(), library))
        
    def notify_media_servers(self, monitor):
        if self.notify_plex == True and monitor.plex_library_valid == True:
            self.plex_api.set_library_scan(monitor.plex_library)
            self._log_moved_to_target(monitor.name, monitor.plex_library, 'plex')
        if self.notify_emby == True and monitor.emby_library_valid == True:
            self.emby_api.set_library_scan()
            self._log_moved_to_target(monitor.name, monitor.emby_library, 'emby')
    
    def _get_all_paths_in_path(self, path):
        return_paths = []

        q = [path]
        while q:
            current_path = q[0]
            del q[0]

            return_paths.append(current_path)

            for filename in os.listdir(current_path):
                entry_filepath = os.path.join(current_path, filename)
                if os.path.isdir(entry_filepath) is False:
                    continue

                q.append(entry_filepath)
        
        return return_paths
    
    def _add_inotify_watch(self, i, path, scan_mask):
        new_paths = self._get_all_paths_in_path(path)
        
        with self.watched_paths_lock:
            for new_path in new_paths:
                if new_path not in self.watched_paths:
                    i.add_watch(new_path, scan_mask)
                    self.watched_paths.append(new_path)
    
    def _delete_inotify_watch(self, path):
        if path in self.watched_paths:
            new_monitor_paths = []
            for watch_path in self.watched_paths:
                if watch_path.startswith(path) == False:
                    new_monitor_paths.append(watch_path)

            with self.watched_paths_lock:
                self.watched_paths = new_monitor_paths
        
    def _monitor(self):
        while self.stop_threads == False:
            if len(self.monitors) > 0:
                current_time = time.time()
                if current_time - self.last_notify_time >= self.seconds_between_notifies:
                    notify_found = False
                    current_index = 0
                    for monitor in self.monitors:
                        if (current_time - monitor.time) >= self.seconds_before_notify:
                            self.notify_media_servers(monitor)
                            self.last_notify_time = current_time
                            notify_found = True
                            break
                        
                        current_index += 1
    
                    if notify_found == True:
                        with self.monitor_lock:
                            self.monitors.pop(current_index)
            
            if len(self.check_new_paths):
                new_path_list = []
                current_time = time.time()
                for check_path in self.check_new_paths:
                    if current_time - check_path.time >= 1.0:
                        if check_path.deleted == True:
                            self._delete_inotify_watch(check_path.path)
                        else:
                            self._add_inotify_watch(check_path.i, check_path.path, check_path.scan_mask)
                    else:
                        new_path_list.append(check_path)
                
                with self.lock_check_new_paths:
                    self.check_new_paths = new_path_list
                
            time.sleep(self.sleep_time)
        
        self.logger.info('{}{}{}: Stopping monitor thread'.format(self.service_ansi_code, self.__module__, get_log_ansi_code()))
    
    def _add_file_monitor(self, path, scan):
        found = False
        current_time = time.time()
        for monitor in self.monitors:
            if monitor.path == path or (monitor.plex_library == scan.plex_library and monitor.emby_library == scan.emby_library):
                monitor.time = current_time
                found = True
                
                if monitor.path != path:
                    self.logger.info('{}{}{}: Scan moved to monitor {}name={}{} {}path={}{}'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), self.tag_ansi_code, get_log_ansi_code(), scan.name, self.tag_ansi_code, get_log_ansi_code(), path))
        
        if found == False:
            with self.monitor_lock:
                self.monitors.append(ScanInfo(scan.name, path, scan.plex_library_valid, scan.plex_library, scan.emby_library_valid, scan.emby_library, current_time))
            
            self.logger.info('{}{}{}: Scan moved to monitor {}name={}{} {}path={}{}'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), self.tag_ansi_code, get_log_ansi_code(), scan.name, self.tag_ansi_code, get_log_ansi_code(), path))
        
    def monitor_path(self, scan):
        self.logger.info('{}{}{}: Starting monitor {}name={}{} {}path={}{}'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), self.tag_ansi_code, get_log_ansi_code(), scan.name, self.tag_ansi_code, get_log_ansi_code(), scan.path))
        
        scanner_mask =  (inotify.constants.IN_MODIFY | inotify.constants.IN_MOVED_FROM | inotify.constants.IN_MOVED_TO | 
                        inotify.constants.IN_CREATE | inotify.constants.IN_DELETE)
        
        i = inotify.adapters.Inotify()
        
        self._add_inotify_watch(i, scan.path, scanner_mask)
            
        for event in i.event_gen(yield_nones=False):
            (_, type_names, path, filename) = event
            if filename != '':
                is_delete = 'IN_DELETE' in type_names or 'IN_MOVED_FROM' in type_names
                if 'IN_ISDIR' in type_names and ('IN_CREATE' in type_names or 'IN_MOVED_TO' in type_names or is_delete):
                    with self.lock_check_new_paths:
                        self.check_new_paths.append(CheckPathData('{}/{}'.format(path, filename), i, scanner_mask, time.time(), is_delete))
                path_valid = True
                for folder_name in self.ignore_folder_with_name:
                    if folder_name in path:
                        path_valid = False
                        break
                    
                if len(self.valid_file_extensions) > 0:
                    path_valid = False
                    for valid_extension in self.valid_file_extensions:
                        if filename.endswith(valid_extension):
                            path_valid = True
                            break
                        
                if path_valid == True:
                    self._add_file_monitor(path, scan)
            
            if self.stop_threads == True:
                self.logger.info('{}{}{}: Stopping watch {}name={}{} {}path={}{}'.format(self.service_ansi_code, self.__module__, get_log_ansi_code(), self.tag_ansi_code, get_log_ansi_code(), scan.name, self.tag_ansi_code, get_log_ansi_code(), scan.path))
                break
        
    def start(self):
        for scan in self.scans:
            thread = Thread(target=self.monitor_path, args=(scan,)).start()
            self.threads.append(thread)
        
        self.monitor_thread = Thread(target=self._monitor, args=()).start()
        
    def init_scheduler_jobs(self):
        self.logger.info('{}{}{} Enabled'.format(self.service_ansi_code, self.__module__, get_log_ansi_code()))
        self.start()
