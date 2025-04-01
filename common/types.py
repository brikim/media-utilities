from dataclasses import dataclass, field


@dataclass
class UserPlexInfo:
    server_name: str
    user_name: str
    friendly_name: str
    user_id: int
    can_sync: bool


@dataclass
class UserEmbyInfo:
    server_name: str
    user_name: str
    user_id: str


@dataclass
class UserInfo:
    plex_users: list[UserPlexInfo] = field(default_factory=list)
    emby_users: list[UserEmbyInfo] = field(default_factory=list)


@dataclass
class CronInfo:
    hours: str
    minutes: str


@dataclass
class MediaServerInfo:
    plex_valid: bool
    emby_valid: bool
    emby_library_id: str
