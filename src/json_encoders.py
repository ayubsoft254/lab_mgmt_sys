"""
Custom JSON encoders for the Lab Management System.
"""
import json
from datetime import datetime, date, time
from decimal import Decimal
from django.http import JsonResponse as DjangoJsonResponse


class DateTimeEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that can handle datetime, date, and time objects.
    """
    def default(self, obj):
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class JsonResponse(DjangoJsonResponse):
    """
    Custom JsonResponse that uses DateTimeEncoder to handle datetime objects.
    """
    def __init__(self, data, **kwargs):
        super().__init__(data, encoder=DateTimeEncoder, **kwargs)
