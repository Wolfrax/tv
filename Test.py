import json
from dateutil import parser


with open('ws.json') as f:
    obs = json.load(f)

    last_dt = parser.parse(obs[-1]['Sample'])
    ind = 0

    for item in obs:
        if (last_dt - parser.parse(item['Sample'])).total_seconds() <= 2*60*60:
            ind -= 1

    print(json.dumps({'ts': '2024-10-28', 'rain': [1, 2, 3]}, indent=4))

