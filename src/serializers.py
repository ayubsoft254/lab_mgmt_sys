"""
Custom serializers for the Lab Management System.
"""
import json
from datetime import datetime, date
from django.contrib.sessions.serializers import JSONSerializer


class DateTimeJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that can handle datetime and date objects.
    """
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


class DateTimeAwareJSONSerializer(JSONSerializer):
    """
    Custom session serializer that can handle datetime and date objects.
    """
    def dumps(self, obj):
        """Serialize object to JSON with datetime support."""
        return json.dumps(obj, cls=DateTimeJSONEncoder, separators=(',', ':')).encode('utf-8')

    def loads(self, data):
        """Deserialize JSON to object."""
        return json.loads(data.decode('utf-8'))
