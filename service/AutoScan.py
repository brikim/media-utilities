
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
from service.ServiceBase import ServiceBase

@dataclass
class ScanInfo:
    name: str
    path: str
    plex_library_valid: bool
    plex_library: str
    emby_library_valid: bool
    emby_library: str
    emby_library_id: str
    time: float
    
@dataclass
class CheckPathData:
    path: str
    i: inotify.adapters.Inotify
    scan_mask: int
    time: float
    deleted: bool
    
class AutoScan(ServiceBase):
    def __init__(self, ansi_code, plex_api, emby_api, config, logger, scheduler):
        super().__init__(ansi_code, self.__module__, config, logger, scheduler)
        
        self.plex_api = plex_api
        self.emby_api = emby_api
        self.ignore_folder_with_name = []
        self.valid_file_extensions = []
        
        self.seconds_monitor_rate = 0
        self.seconds_before_notify = 0
        self.seconds_between_notifies = 0
        self.seconds_before_inotify_modify = 0
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
        
        self.check_new_paths_lock = threading.Lock()
        self.check_new_paths = []
        
        try:
            self.seconds_monitor_rate = max(config['seconds_monitor_rate'], 1)
            self.seconds_before_notify = max(config['seconds_before_notify'], 30)
            self.seconds_between_notifies = max(config['seconds_between_notifies'], 10)
            self.seconds_before_inotify_modify = max(config['seconds_before_inotify_modify'], 1)
            
            if 'notify_plex' in config and config['notify_plex'] == 'True':
                if self.plex_api.get_valid() == True:
                    self.notify_plex = True
                else:
                    self.log_warning('Notify {} is true but API not valid {}'.format(self.formatted_plex, self.get_tag('plex_valid', self.plex_api.get_valid())))
            
            if 'notify_emby' in config and config['notify_emby'] == 'True':
                if self.emby_api.get_valid() == True:
                    self.notify_emby = True
                else:
                    self.log_warning('Notify {} is true but API not valid {}'.format(self.formatted_emby, self.get_tag('emby_valid', self.emby_api.get_valid())))
            
            for scan in config['scans']:
                plex_library = ''
                if self.notify_plex == True and 'plex_path' in scan:
                    plex_library = self.plex_api.get_library_name_from_path(scan['plex_path'])
                
                emby_library_name = ''
                emby_library_id = ''
                if self.notify_emby == True and 'emby_path' in scan:
                    emby_library = self.emby_api.get_library_from_path(scan['emby_path'])
                    emby_library_name = emby_library['Name']
                    emby_library_id = emby_library['Id']
                
                self.scans.append(ScanInfo(scan['name'], scan['container_path'], plex_library != '', plex_library, emby_library_name != '', emby_library_name, emby_library_id, 0.0))
            
            for folder in config['ignore_folder_with_name']:
                self.ignore_folder_with_name.append(folder['ignore_folder'])
                
            if config['valid_file_extensions'] != '':
                self.valid_file_extensions = config['valid_file_extensions'].split(',')
                
                
        except Exception as e:
            self.log_error('Read config {}error={}{}'.format(self.get_tag('error', e)))
    
    def shutdown(self):
        self.stop_threads = True
        
        temp_file_path = '/temp.txt'
        
        # Create a temp file to notify the inotify adapters
        for scan in self.scans:
            temp_file = scan.path + temp_file_path
            with open(temp_file, 'w') as file:
                file.write('BREAK')
            
        # allow time for the events
        time.sleep(1)
        
        with self.monitor_lock:
            self.monitors.clear()
                            
        # clean up the temp files
        for scan in self.scans:
            temp_file = scan.path + temp_file_path
            os.remove(temp_file)
        
        self.log_info('Successful shutdown')
    
    def _log_moved_to_target(self, name, target, library):
        self.log_info('Monitor moved to target {} {} {}'.format(self.get_tag('name', name), self.get_tag('target', target), self.get_tag('library', library)))
        
    def _notify_media_servers(self, monitor):
        if self.notify_plex == True and monitor.plex_library_valid == True:
            self.plex_api.set_library_scan(monitor.plex_library)
            self._log_moved_to_target(monitor.name, self.formatted_plex, monitor.plex_library)
        if self.notify_emby == True and monitor.emby_library_valid == True:
            self.emby_api.set_library_scan(monitor.emby_library_id)
            self._log_moved_to_target(monitor.name, self.formatted_emby, monitor.emby_library)
    
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
        # Add the path and all sub-paths to the notify list
        new_paths = self._get_all_paths_in_path(path)
        
        with self.watched_paths_lock:
            for new_path in new_paths:
                if new_path not in self.watched_paths:
                    i.add_watch(new_path, scan_mask)
                    self.watched_paths.append(new_path)
    
    def _delete_inotify_watch(self, i, path):
        # inotify automatically deletes watches of deleted paths
        # cleanup our local path list when a path is deleted
        with self.watched_paths_lock:
            if path in self.watched_paths:
                new_monitor_paths = []
                for watch_path in self.watched_paths:
                    if watch_path.startswith(path) == True:
                        i.remove_watch(watch_path, True)
                    else:
                        new_monitor_paths.append(watch_path)

                self.watched_paths = new_monitor_paths
        
    def _monitor(self):
        while self.stop_threads == False:
            
            # Process any monitors currently in the system
            with self.monitor_lock:
                if len(self.monitors) > 0:
                    current_time = time.time()
                    if current_time - self.last_notify_time >= self.seconds_between_notifies:
                        current_monitor = None
                        for monitor in self.monitors:
                            if (current_time - monitor.time) >= self.seconds_before_notify:
                                self._notify_media_servers(monitor)
                                current_monitor = monitor
                                self.last_notify_time = current_time
                                break
                            
                        # A monitor was finished and servers notified remove it from the list
                        if current_monitor is not None:
                            # If servers were just notified for this name remove all monitors for the same name since
                            # the server refresh is by library not by item
                            new_monitors = []
                            for monitor in self.monitors:
                                if monitor.name != current_monitor.name:
                                    new_monitors.append(monitor)

                                self.monitors = new_monitors
            
            # Check if any new paths need to be added to the inotify list
            with self.check_new_paths_lock:
                if len(self.check_new_paths) > 0:
                    new_path_list = []
                    current_time = time.time()
                    for check_path in self.check_new_paths:
                        if (current_time - check_path.time) >= self.seconds_before_inotify_modify:
                            if check_path.deleted == True:
                                self._delete_inotify_watch(check_path.i, check_path.path)
                            else:
                                # Make sure the path still exists before continue
                                if os.path.isdir(check_path.path) == True:
                                    self._add_inotify_watch(check_path.i, check_path.path, check_path.scan_mask)
                        else:
                            new_path_list.append(check_path)
                
                        # Set the check new paths to the new list
                        self.check_new_paths = new_path_list
                
            time.sleep(self.seconds_monitor_rate)
        
        self.log_info('Stopping monitor thread')
    
    def _add_file_monitor(self, path, scan):
        found = False
        current_time = time.time()
        
        # Check if this path or library already exists in the list
        #   If the library already exists just update the time to wait since we can only notify per library to update not per item
        with self.monitor_lock:
            for monitor in self.monitors:
                # If the name is the same this monitor belongs to the same library so update the time
                if monitor.name == scan.name:
                    # If the path is the same this is just an update to an existing monitor
                    if monitor.path == path:
                        found = True
                    monitor.time = current_time
        
        # No monitor found for this item add it to the monitor list
        if found == False:
            with self.monitor_lock:
                self.monitors.append(ScanInfo(scan.name, path, scan.plex_library_valid, scan.plex_library, scan.emby_library_valid, scan.emby_library, scan.emby_library_id, current_time))
            
            self.log_info('Scan moved to monitor {} {}'.format(self.get_tag('name', scan.name), self.get_tag('path', path)))
        
    def _monitor_path(self, scan):
        self.log_info('Starting monitor {} {}'.format(self.get_tag('name', scan.name), self.get_tag('path', scan.path)))
        
        scanner_mask =  (inotify.constants.IN_MODIFY | inotify.constants.IN_MOVED_FROM | inotify.constants.IN_MOVED_TO | 
                        inotify.constants.IN_CREATE | inotify.constants.IN_DELETE)
        
        # Setup the inotify watches for the current folder and all sub-folders
        i = inotify.adapters.Inotify()
        self._add_inotify_watch(i, scan.path, scanner_mask)
            
        for event in i.event_gen(yield_nones=False):
            (_, type_names, path, filename) = event
            if filename != '':
                # New path check. This will add or delete scans if folders are added or removed
                is_delete = 'IN_DELETE' in type_names or 'IN_MOVED_FROM' in type_names
                if 'IN_ISDIR' in type_names and ('IN_CREATE' in type_names or 'IN_MOVED_TO' in type_names or is_delete):
                    with self.check_new_paths_lock:
                        self.check_new_paths.append(CheckPathData('{}/{}'.format(path, filename), i, scanner_mask, time.time(), is_delete))
                
                # Check if this path is in the ignore folder list. If so mark the path as not valid
                path_valid = True
                for folder_name in self.ignore_folder_with_name:
                    if folder_name in path:
                        path_valid = False
                        break
                    
                # Check if the extension of the added file is valid
                extension_valid = True
                if path_valid == True and len(self.valid_file_extensions) > 0:
                    extension_valid = False
                    for valid_extension in self.valid_file_extensions:
                        if filename.endswith(valid_extension):
                            extension_valid = True
                            break
                
                # If all the checks passed add this as a monitor
                if path_valid == True and extension_valid == True:
                    self._add_file_monitor(path, scan)
            
            if self.stop_threads == True:
                self.log_error('Stopping watch {} {}'.format(self.get_tag('name', scan.name), self.get_tag('path', scan.path)))
                break
        
    def start(self):
        for scan in self.scans:
            thread = Thread(target=self._monitor_path, args=(scan,)).start()
            self.threads.append(thread)
        
        self.monitor_thread = Thread(target=self._monitor, args=()).start()
        
    def init_scheduler_jobs(self):
        self.log_service_enabled()
        self.start()
