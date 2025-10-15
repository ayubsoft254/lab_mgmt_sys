"""
Custom error handler views for the Lab Management System.
These views render custom error pages with consistent styling.
"""
from django.shortcuts import render
import uuid


def bad_request(request, exception=None):
    """
    Custom 400 Bad Request error handler.
    
    Args:
        request: The HTTP request object
        exception: The exception that triggered this error (optional)
    
    Returns:
        HttpResponse with the 400 error page
    """
    context = {
        'request_id': str(uuid.uuid4())[:8],
    }
    return render(request, '400.html', context, status=400)


def permission_denied(request, exception=None):
    """
    Custom 403 Forbidden error handler.
    
    Args:
        request: The HTTP request object
        exception: The exception that triggered this error (optional)
    
    Returns:
        HttpResponse with the 403 error page
    """
    context = {
        'request_id': str(uuid.uuid4())[:8],
    }
    return render(request, '403.html', context, status=403)


def page_not_found(request, exception=None):
    """
    Custom 404 Not Found error handler.
    
    Args:
        request: The HTTP request object
        exception: The exception that triggered this error (optional)
    
    Returns:
        HttpResponse with the 404 error page
    """
    context = {
        'request_id': str(uuid.uuid4())[:8],
    }
    return render(request, '404.html', context, status=404)


def server_error(request):
    """
    Custom 500 Internal Server Error handler.
    
    Args:
        request: The HTTP request object
    
    Returns:
        HttpResponse with the 500 error page
    """
    context = {
        'request_id': str(uuid.uuid4())[:8],
    }
    return render(request, '500.html', context, status=500)
