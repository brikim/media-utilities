""" Common Types to be used by Services """

from dataclasses import dataclass, field


@dataclass
class UserPlexInfo:
    """ Class representing a Plex User """
    server_name: str
    user_name: str
    friendly_name: str
    user_id: int
    can_sync: bool


@dataclass
class UserEmbyInfo:
    """ Class representing a Emby User """
    server_name: str
    user_name: str
    user_id: str


@dataclass
class UserInfo:
    """ Class representing a User group of Plex and Emby users """
    plex_users: list[UserPlexInfo] = field(default_factory=list)
    emby_users: list[UserEmbyInfo] = field(default_factory=list)


@dataclass
class CronInfo:
    """ Class representing a Cron Expression """
    hours: str
    minutes: str


@dataclass
class MediaServerInfo:
    """ Class representing a Media Server Connection """
    plex_valid: bool
    emby_valid: bool
    emby_library_id: str
