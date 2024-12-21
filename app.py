"""
Media Utilities
"""
import sys
import os
import json
import logging
import colorlog
import signal
import time
from logging.handlers import RotatingFileHandler
from apscheduler.schedulers.blocking import BlockingScheduler

from api.plex import PlexAPI
from api.tautulli import TautulliAPI
from api.emby import EmbyAPI
from api.jellystat import JellystatAPI
from common.gotify_handler import GotifyHandler
from service.SyncWatched import SyncWatched
from service.DeleteWatched import DeleteWatched
from service.DvrMaintainer import DvrMaintainer

# Global Variables #######
logger = logging.getLogger(__name__)
scheduler = BlockingScheduler()

# Api
plex_api = None
tautulli_api = None
emby_api = None
jellystat_api = None
        
# Available Services
sync_watched_service = None
delete_watched_service = None
dvr_maintainer_service = None
##########################

def handle_sigterm(signum, frame):
    logger.info("SIGTERM received, shutting down ...")
    scheduler.shutdown(wait=True)
    sys.exit(0)

def do_nothing():
    time.sleep(1)

conf_loc_path_file = ""
config_file_valid = True
if "CONFIG_PATH" in os.environ:
    conf_loc_path_file = os.environ['CONFIG_PATH'].rstrip('/')
else:
    config_file_valid = False

if config_file_valid == True and os.path.exists(conf_loc_path_file) == True:
    try:
        # Opening JSON file
        f = open(conf_loc_path_file, 'r')
        data = json.load(f)

        # Main script run ####################################################

        # Set up signal termination handle
        signal.signal(signal.SIGTERM, handle_sigterm)

        #date format
        date_format = '%Y-%m-%d %H:%M:%S'

        # Set up the logger
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', date_format)

        # Create a file handler to write logs to a file
        rotating_handler = RotatingFileHandler('/logs/media-utility.log', maxBytes=50000, backupCount=5)
        rotating_handler.setLevel(logging.DEBUG)
        rotating_handler.setFormatter(formatter)

        log_colors = {
            'DEBUG': 'cyan',
            'INFO': 'light_green',
            'WARNING': 'light_yellow',
            'ERROR': 'light_red',
            'CRITICAL': 'bold_red'}

        # Create a stream handler to print logs to the console
        console_info_handler = colorlog.StreamHandler()
        console_info_handler.setLevel(logging.INFO)
        console_info_handler.setFormatter(colorlog.ColoredFormatter(
            '%(white)s%(asctime)s %(light_white)s- %(log_color)s%(levelname)s %(light_white)s- %(message)s', date_format, log_colors=log_colors))

        gotify_handler = None
        if data['enable_gotify_logger'] == 'True':
            gotify_handler = GotifyHandler(data['gotify_url'], data['gotify_app_token'], data['gotify_priority'])
            gotify_handler.setLevel(logging.WARNING)
            gotify_handler.setFormatter(formatter)
            
        # Add the handlers to the logger
        logger.addHandler(rotating_handler)
        logger.addHandler(console_info_handler)
        if gotify_handler is not None:
            logger.addHandler(gotify_handler)
        
        # Create all the api servers
        plex_api = PlexAPI(data['plex_url'], data['plex_api_key'], data['plex_admin_user_name'], logger)
        tautulli_api = TautulliAPI(data['tautulli_url'], data['tautulli_api_key'], logger)
        emby_api = EmbyAPI(data['emby_url'], data['emby_api_key'], logger)
        jellystat_api = JellystatAPI(data['jellystat_url'], data['jellystat_api_key'], logger)
        
        logger.info('Starting Run *************************************')
        
        # Create the services ####################################
        
        # Create the Sync Watched Status Service
        if data['sync_watched']['enabled'] == 'True':
            sync_watched_service = SyncWatched(plex_api, tautulli_api, emby_api, jellystat_api, data['sync_watched'], logger, scheduler)
        if data['delete_watched']['enabled'] == 'True':
            delete_watched_service = DeleteWatched(plex_api, tautulli_api, emby_api, jellystat_api, data['delete_watched'], logger, scheduler)
        if data['dvr_maintainer']['enabled'] == 'True':
            dvr_maintainer_service = DvrMaintainer(plex_api, emby_api, data['dvr_maintainer'], logger, scheduler)
        
        # ########################################################
        
        # Init the services ######################################
        if sync_watched_service is not None:
            sync_watched_service.init_scheduler_jobs()
        if delete_watched_service is not None:
            delete_watched_service.init_scheduler_jobs()
        if dvr_maintainer_service is not None:
            dvr_maintainer_service.init_scheduler_jobs()
        # ########################################################
        
        # Add a job to do nothing to keep the script alive
        scheduler.add_job(do_nothing, trigger='interval', hours=24)
        
        # Start the scheduler for all jobs
        scheduler.start()
        
    except Exception as e:
        logger.error("Error starting: {}".format(e))
else:
    sys.stderr.write("Error opening config file {}\n".format(conf_loc_path_file))

# END Main script run ####################################################