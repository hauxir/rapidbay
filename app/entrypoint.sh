#!/bin/bash
nginx
uvicorn app:app --uds rapidbay.sock --workers $(( 2 * `cat /proc/cpuinfo | grep 'core id' | wc -l` + 1 )) --timeout-keep-alive 900 --limit-max-requests 0 & uvicorn rapidbaydaemon:app --uds rapidbaydaemon.sock --workers 1
