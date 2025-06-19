import json
from datetime import datetime

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

data = {
    "name": "John",
    "timestamp": datetime.now()
}

print(json.dumps(data, cls=CustomEncoder))