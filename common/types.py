from dataclasses import dataclass

@dataclass
class UserInfo:
    plex_user_name: str
    plex_user_id: int
    emby_user_name: str
    emby_user_id: str
    
@dataclass
class CronInfo:
    hours: str
    minutes: str
