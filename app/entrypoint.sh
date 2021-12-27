#!/bin/bash
nginx
gunicorn --limit-request-line 10000 -w 1 --bind unix:rapidbay.sock app:app --access-logfile -
