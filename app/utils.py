import json
from decimal import Decimal
from datetime import datetime, timezone

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def get_utc_now():
    return datetime.now(timezone.utc).isoformat()
