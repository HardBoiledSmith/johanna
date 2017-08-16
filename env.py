import json
import sys

config_path = '.'
if sys.path[0]:
    config_path = sys.path[0]

# Load Config.json
env = json.load(open('%s/config.json' % config_path))
