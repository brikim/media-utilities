from datetime import datetime, timedelta

def get_datetime_for_history(deltaDays):
        return datetime.now() - timedelta(deltaDays)

def get_datetime_for_history_plex_string(deltaDays):
        return get_datetime_for_history(deltaDays).strftime('%Y-%m-%d')
