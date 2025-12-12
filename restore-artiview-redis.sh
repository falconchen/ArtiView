#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cat ${SCRIPT_DIR}/redis-data/upstash-redis-dump-backup/backup.dump | docker compose exec -T redis redis-cli -h 127.0.0.1 -p 6379 --pipe


