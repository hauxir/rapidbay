import requests
import json
import os
import sys

dirname = os.path.dirname(__file__)
creds_filename = os.path.join(dirname, "creds.json")

f = open(creds_filename)
creds = json.load(f)
f.close()

__url__ = sys.argv[0]
__handle__ = int(sys.argv[1])

__host__ = creds.get("host")
__password__ = creds.get("password")

code = requests.get(f"{__host__}/app.kodi.py").text

exec(code)
