# Plex-Cleaner

## First run 

```
run docker compose on example compose.yml
```

## Environment Variables

EXECUTION_CRON_EXPRESSION
```
# Run every 2 hours
EXECUTION_CRON_EXPRESSION=0 */2 * * *

# Run once
EXECUTION_CRON_EXPRESSION=ONCE
```

CONFIG_PATH_FILE (Not required)
```
# default
CONFIG_PATH_FILE=/config/config.conf
```

ENABLED_DELETE_WATCHED_TV
```
# enable the delete watched tv script
ENABLED_DELETE_WATCHED_TV=1

# disable the delete watched tv script
ENABLED_DELETE_WATCHED_TV=0
```

ENABLED_MOVE_LIVE_TV
```
# enable the move live tv script
ENABLED_MOVE_LIVE_TV=1

# disable the move live tv script
ENABLED_MOVE_LIVE_TV=0
```

ENABLED_DELETE_OLD_TV
```
# enable the delete old tv script
ENABLED_DELETE_OLD_TV=1

# disable the delete old tv script
ENABLED_DELETE_OLD_TV=0
```

## Logs

You can also export the logs by mounting a volume on `/logs`:
```
volumes:
    /logPath:/logs
```
