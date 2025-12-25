#!/bin/bash
nginx
uvicorn app:app --uds rapidbay.sock --workers 1 --timeout-keep-alive 900 --limit-max-requests 0
