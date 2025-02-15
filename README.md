# Media-Utilities
Media-Utilities is a collection of services to assist in your Plex and Emby media management.

1. Sync Watched Status
* Allows the syncing of watch status from plex to emby
* Allows the syncing of watch status from emby to plex. For admin of plex server only.
2. Delete Watched (DVR function)
* Delete watched items after a specified time period
* Uses Tautulli or Jellystat to get watched items
3. DVR Maintainer
* Allows user to specify a show and how to keep episodes
* Can be keep last X days
* Can be keep length X days
4. Folder Cleanup
* Cleanup empty folders and notify media servers of delete

Each service can be configured independently. Each service allows for a cron rate on when to run.

## Installing Media-Utilities
Media-Utilities offers a pre-compiled [docker image](https://hub.docker.com/repository/docker/brikim/media-utilities/general)

### Usage
Use docker compose to run Media-Utilities

### compose.yml
```yaml
---
services:
  media-utilities:
    image: brikim/media-utilities:latest
    container_name: media-utilities
    security_opt:
      - no-new-privileges:true
    environment:
      - TZ=America/Chicago
    volumes:
      - /docker/media-utilities/config:/config
      - /docker/media-utilities/logs:/logs
      - /pathToMedia:/media
    restart: unless-stopped
```
> [!NOTE]
> 📝 /media folder can not be read only for all services to function correctly

### Environment Variables
| Env | Function |
| :------- | :------------------------ |
| TZ       | specify a timezone to use |

### Volume Mappings
| Volume | Function |
| :------- | :------------------------ |
| /config  | Path to a folder containing config.yml used to setup Media-Utilities |
| /logs    | Path to a folder to store Media-Utilities log files |
| /media   | Path to your media files. Used by services to monitor your media files |

### Configuration File
A configuration file is required to use Media-Utilities. Create a config.yml file in the volume mapped to /config

#### config.yml
```yaml
{
    "plex_url": "http://0.0.0.0:32400",
    "plex_api_key": "",
    "plex_admin_user_name": "AdminUserName",
    "plex_media_path": "/media/",

    "tautulli_url": "http://0.0.0.0:0000",
    "tautulli_api_key": "",

    "emby_url": "http://0.0.0.0:8096",
    "emby_api_key": "",
    "emby_media_path": "/media/",

    "jellystat_url": "http://0.0.0.0:8888",
    "jellystat_api_key": "",

    "gotify_logging": {
        "enabled": "True",
        "url": "",
        "app_token": "",
        "message_title": "Title of message",
        "priority": 6
    },

    "sync_watched": {
        "enabled": "True",
        "cron_run_rate": "0 */2",

        "users": [
            {"plex_name": "User1", "can_sync_plex_watch": "True", "emby_name": "User1"},
            {"plex_name": "User2", "can_sync_plex_watch": "False", "emby_name": "User2"}
        ]
    },

    "delete_watched": {
        "enabled": "True",
        "cron_run_rate": "0 */2",
        "delete_time_hours": 24,
        "users": [
            {"plex_name": "User1", "emby_name": "User1"},
            {"plex_name": "User2", "emby_name": "User2"}
        ],
        "libraries": [
            {
                "plex_library_name": "PlexLibraryName", "plex_media_path": "/pathPlexUsesForMedia",
                "emby_library_name": "EmbyLibraryName", "emby_media_path": "/pathEmbyUsesForMedia",
                "utilities_path": "/pathUtilitiesToMedia"
            }
        ]
    },

    "dvr_maintainer": {
        "enabled": "True",
        "cron_run_rate": "0 */2",
        "_comment": "shows actions include KEEP_LAST_ followed by an integer of total shows to keep and KEEP_LENGTH_DAYS_ followed by an integer of days",
        "libraries": [
            {
                "plex_library_name": "PlexLibraryNameThatContainsName1",
                "emby_library_name": "EmbyLibraryNameThatContainsName1",
                "utilities_path": "/pathUtilitiesToMedia",
                "shows": [
                    {"name": "DirectoryNameInUtilitiesLibraryPath", "action": "KEEP_LAST_5"},
                    {"name": "DirectoryNameInUtilitiesLibraryPath2", "action": "KEEP_LENGTH_DAYS_7"}
                ]
            },
            {
                "plex_library_name": "PlexLibraryNameThatContainsName2",
                "emby_library_name": "EmbyLibraryNameThatContainsName2",
                "utilities_path": "/pathUtilitiesToMedia2",
                "shows": [
                    {"name": "DirectoryNameInUtilitiesLibraryPath", "action": "KEEP_LAST_5"},
                    {"name": "DirectoryNameInUtilitiesLibraryPath2", "action": "KEEP_LENGTH_DAYS_7"}
                ]
            }
        ]
    },

    "folder_cleanup": {
        "enabled": "True",
        "cron_run_rate": "0 */2",
        "paths_to_check": [
            {"path": "/pathToCheckForEmpty", "plex_library_name": "nameOfPlexLibrary", "emby_library_name": "nameOfEmbyLibrary"}
        ],
        "_comment_ignore_folder_in_check": "Folders to ignore for the path to be considered empty",
        "ignore_folder_in_empty_check": [
            {"ignore_folder": "someFolderToIgnore"}
        ],
        "_comment_ignore_files_in_check": "Files to ignore for the path to be considered empty",
        "ignore_file_in_empty_check": [
            {"ignore_file": "someFileToIgnore"}
        ]
    }
}
```

#### Option Descriptions
You only have to define the variables for servers in your system. For plex only define plex_url and plex_api_key in your file. The emby and jellyfin variables are not required.
| Media Server | Function |
| :----------- | :------------------------ |
| plex_url             | Url to your plex server (Make sure you include the port if not reverse proxy) |
| plex_api_key         | API Key to access your plex server |
| plex_admin_user_name | Name of the admin user for the plex server |
| plex_media_path      | Path your plex media server is using in the container to its media |
| tautulli_url         | Url to your tautulli server (Make sure you include the port if not reverse proxy) |
| tautulli_api_key     | API key to access your tautulli server |
| emby_url             | Url to your emby server (Make sure you include the port if not reverse proxy) |
| emby_api_key         | API Key to access your emby server |
| emby_media_path      | Path your emby media server is using in the container to its media |
| jellystat_url         | Url to your jellystat server (Make sure you include the port if not reverse proxy) |
| jellystat_api_key     | API Key to access your jellystat server |

#### Gotify Logging
Not required unless wanting to send Warnings or Errors to Gotify
| Gotify | Function |
| :--------------- | :------------------------ |
| enabled          | Enable the function with 'True' |
| url              | Url including port to your gotify server |
| app_token        | Gotify app token to be used to send notifications |
| message_title    | Title to put in the title bar of the message |
| priority         | The priority of the message to send to gotify |

#### Sync Watched configuration
Sync Watched service will sync the watch status between Plex and Emby users. Requires Tautulli and Jellystat to work. Define a plex user name to sync to an emby user name and vice versa.

| sync_watched | Function |
| :--------------- | :------------------------ |
| enabled       | Enable the sync watch service |
| cron_run_rate | Rate at which to run this service. Cron format but only uses minutes and hours |
| users         | A list of users to sync watch status |

1 to many users can be listed for sync watched
| users | Function |
| :--------------- | :------------------------ |
| plex_name | The plex user name to sync watch status |
| can_sync_plex_watch | This should be True for the admin user of the server only |
| emby_name | The emby user name to sync watch status |

#### Delete Watched
Plex by default does not allow users to delete media. This service was intended to be used on a TV Recordings library but can be used however you want. Define a set of libraries and users. If the service detects an item has been watched by a defined user it will delete the item after a defined time period.

| delete_watched | Function |
| :--------------- | :------------------------ |
| enabled           | Enable the delete watched service |
| cron_run_rate     | Rate at which to run this service. Cron format but only uses minutes and hours |
| delete_time_hours | How long to wait in hours after a show has been watched to delete |
| users             | A list of users to monitor for watched status |
| libraries         | A list of libraries to monitor for defined user watches |

1 to many users can be listed for sync watched
| users | Function |
| :--------------- | :------------------------ |
| plex_name | The plex user name to to monitor for watches (Optional) |
| emby_name | The emby user name to to monitor for watches (Optional) |

1 to many libraries can be listed for sync watched
| libraries | Function |
| :--------------- | :------------------------ |
| plex_library_name | The name of the plex library to monitor for user watches (Optional) |
| emby_library_name | The name of the emby library to monitor for user watches (Optional) |
| utilities_path    | The path in the media-utilities container that corresponds to the plex or emby library media |

#### DVR Maintainer
Plex and Emby have a very basic DVR function for removing media after a certain amount of time or a max episode limit. This service expands on this and allows you to specify a max number of episodes or a length in days a episode is allowed to be on the server.

| dvr_maintainer | Function |
| :--------------- | :------------------------ |
| enabled           | Enable the delete watched service |
| cron_run_rate     | Rate at which to run this service. Cron format but only uses minutes and hours |
| libraries         | A list of libraries to monitor for media deletion |

1 to many libraries can be listed for dvr maintainer
| libraries | Function |
| :--------------- | :------------------------ |
| plex_library_name | Name of the plex library to notify on media deletion (Optional) |
| emby_library_name | Name of the emby library to notify on media deletion (Optional) |
| utilities_path    | Path in the container that corresponds to this libraries media |
| shows             | A list of shows to monitor and how long episodes should be kept |

1 to many shows can be listed for each library
| shows | Function |
| :--------------- | :------------------------ |
| name        | Name of the show to monitor for deletions |
| action      | Action for the keep time/number of this show. Two options are supported. KEEP_LAST_X - Where X is the number of episodes to keep for this show. Must be an integer. Will delete the oldest shows by file timestamp. KEEP_LENGTH_DAYS_X. Where X is the number of days to keep episodes in this show. |

#### Folder cleanup
Will remove empty folders within a specified directory. This can be useful running with DVR Maintainer. Emby will still list a show in the library even though media does not exist in it. This service cleans up empty folders and notified media servers of this change.

| folder_cleanup | Function |
| :--------------- | :------------------------ |
| enabled           | Enable the delete watched service |
| cron_run_rate     | Rate at which to run this service. Cron format but only uses minutes and hours |
| paths_to_check    | A list of paths to check for empty folders |
| ignore_folder_in_empty_check    | A list folder names to ignore empty checks |
| ignore_file_in_empty_check    | A list of files to ignore. If a folder contains this file it will still be considered empty |

1 to many ignore_folder_in_empty_check can be listed
| ignore_folder_in_empty_check | Function |
| :--------------- | :------------------------ |
| path        | Path to check for empty folders |

1 to many ignore_folder_in_empty_check can be listed
| ignore_folder_in_empty_check | Function |
| :--------------- | :------------------------ |
| ignore_folder        | Path to ignore for empty checks. If this path is found the folder will still be considered empty |

1 to many ignore_file_in_empty_check can be listed
| ignore_file_in_empty_check | Function |
| :--------------- | :------------------------ |
| ignore_file        | File to ignore for empty checks. If this file is found the folder will still be considered empty |