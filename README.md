# media-utilities
Currently supports syncing watch status between plex and emby. This utility uses plex, tautulli, emby and jellystat

## First run 

```
run docker compose on example compose.yml
```

## Logs

You can also export the logs by mounting a volume on `/logs`:
```
volumes:
    /logPath:/logs
```
