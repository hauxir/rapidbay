#!/bin/bash
nginx
gunicorn --limit-request-line 10000 --timeout 900 -w $(( 2 * `cat /proc/cpuinfo | grep 'core id' | wc -l` + 1 )) --bind unix:rapidbay.sock app:app --access-logfile - & gunicorn -w 1 --bind unix:rapidbaydaemon.sock rapidbaydaemon:app
