#
#
#

import subprocess
import json

result = subprocess.run(["./halite", "--replay-directory", "replays/", "--results-as-json", "--width 32", "--height 32", "python MyBot.py","python MyBot.py"], stdout=subprocess.PIPE)
resultsJson = result.stdout.decode('utf8')
data = json.loads(resultsJson)
error_log = data['error_logs']
stats = data['stats']

print (data)
