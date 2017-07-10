import json
import sys

# Load Config.json
env = json.load(open('%s/config.json' % sys.path[0]))
