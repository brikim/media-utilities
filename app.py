"""
Media Utilities
"""
import sys
import os
import json
import logging
import signal
import time
from logging.handlers import RotatingFileHandler
from apscheduler.schedulers.blocking import BlockingScheduler

from plexapi.server import PlexServer
from api.tautulli import TautulliServer
from api.emby import EmbyServer
from api.jellystat import JellystatServer
from service.SyncWatched import SyncWatched

# Global Variables #######
logger = logging.getLogger(__name__)
scheduler = BlockingScheduler()
##########################

def handle_sigterm(signum, frame):
    logger.info("SIGTERM received, shutting down ...")
    scheduler.shutdown(wait=True)
    sys.exit(0)

def do_nothing():
    time.sleep(1)

# Main script run ####################################################

# Set up signal termination handle
signal.signal(signal.SIGTERM, handle_sigterm)

# Set up the logger
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Create a file handler to write logs to a file
rotating_handler = RotatingFileHandler('/logs/media-utility.log', maxBytes=10000, backupCount=5)
rotating_handler.setLevel(logging.DEBUG)
rotating_handler.setFormatter(formatter)

# Create a stream handler to print logs to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # You can set the desired log level for console output
console_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(rotating_handler)
logger.addHandler(console_handler)

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
        
        # Create all the api servers
        plex_api = PlexServer(data['plex_url'], data['plex_api_key'])
        tautulli_api = TautulliServer(data['tautulli_url'], data['tautulli_api_key'], logger)
        emby_api = EmbyServer(data['emby_url'], data['emby_api_key'], logger)
        jellystat_api = JellystatServer(data['jellystat_url'], data['jellystat_api_key'], logger)
        
        logger.info('Starting Run *************************************')
        
        # Available Services
        sync_watched_service = None
        
        # Create the services ####################################
        
        # Create the Sync Watched Status Service
        if data['sync_watched']['enabled'] == 'True':
            sync_watched_service = SyncWatched(plex_api, tautulli_api, emby_api, jellystat_api, data['sync_watched'], logger, scheduler)
        # ########################################################
        
        # Init the services ######################################
        if sync_watched_service is not None:
            sync_watched_service.init_scheduler_jobs()
        # ########################################################
        
        # Add a job to do nothing to keep the script alive
        scheduler.add_job(do_nothing, trigger='interval', hours=24)
        
        # Start the scheduler for all jobs
        scheduler.start()
        
    except Exception as e:
        logger.error("Error starting: {}".format(e))

# END Main script run ####################################################