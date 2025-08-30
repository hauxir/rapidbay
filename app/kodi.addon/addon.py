import json
import os
import sys

import requests

dirname = os.path.dirname(__file__)
creds_filename = os.path.join(dirname, "creds.json")

with open(creds_filename) as f:
    creds = json.load(f)

__url__ = sys.argv[0]
__handle__ = int(sys.argv[1])

__host__ = creds.get("host")
__password__ = creds.get("password")

code = requests.get(f"{__host__}/app.kodi.py").text

exec(code)
