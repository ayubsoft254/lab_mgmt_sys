from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.urls import reverse
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class HostValidationMiddleware(MiddlewareMixin):
    """
    Middleware to validate HTTP_HOST header against allowed hosts.
    Rejects requests with invalid hosts to prevent Host header attacks.
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        # Cache allowed hosts for better performance
        self.allowed_hosts = self._get_allowed_hosts()
    
    def _get_allowed_hosts(self):
        """Get and normalize allowed hosts from settings"""
        allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
        
        # Normalize hosts (convert to lowercase, remove ports for comparison)
        normalized_hosts = set()
        for host in allowed_hosts:
            if host == '*':
                # If wildcard is allowed, return early
                return ['*']
            # Remove port if present and normalize
            host_without_port = host.split(':')[0].lower()
            normalized_hosts.add(host_without_port)
            # Also add the original host (with port if present)
            normalized_hosts.add(host.lower())
        
        return list(normalized_hosts)
    
    def _extract_host(self, request):
        """Extract host from request, handling various scenarios"""
        # Get host from HTTP_HOST header
        host = request.META.get('HTTP_HOST', '')
        
        # Handle X-Forwarded-Host for proxy scenarios
        forwarded_host = request.META.get('HTTP_X_FORWARDED_HOST')
        if forwarded_host:
            # Use the first host if multiple are present
            host = forwarded_host.split(',')[0].strip()
        
        return host.lower()
    
    def _is_valid_host(self, host):
        """Check if the host is valid"""
        if not host:
            return False
        
        # If wildcard is allowed, accept all
        if '*' in self.allowed_hosts:
            return True
        
        # Extract host without port for comparison
        host_without_port = host.split(':')[0]
        
        # Check exact match (with and without port)
        if host in self.allowed_hosts or host_without_port in self.allowed_hosts:
            return True
        
        # Check for wildcard subdomains (e.g., *.example.com)
        for allowed_host in self.allowed_hosts:
            if allowed_host.startswith('*.'):
                domain = allowed_host[2:]  # Remove *.
                if host_without_port.endswith('.' + domain) or host_without_port == domain:
                    return True
        
        return False
    
    def process_request(self, request):
        """Process incoming request and validate host"""
        host = self._extract_host(request)
        
        if not self._is_valid_host(host):
            # Log the suspicious request
            logger.warning(
                f"Invalid host header detected: '{host}' from IP: {self._get_client_ip(request)}"
            )
            
            # Return 400 Bad Request for invalid hosts
            return HttpResponseBadRequest(
                "Invalid Host header. Request rejected for security reasons.",
                content_type="text/plain"
            )
        
        # Host is valid, continue processing
        return None
    
    def _get_client_ip(self, request):
        """Get client IP address, handling proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class EnhancedHostValidationMiddleware(MiddlewareMixin):
    """
    Enhanced version with additional security features
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.allowed_hosts = self._get_allowed_hosts()
        self.suspicious_hosts = set()  # Track suspicious hosts
        self.max_suspicious_requests = getattr(settings, 'MAX_SUSPICIOUS_HOST_REQUESTS', 10)
    
    def _get_allowed_hosts(self):
        """Get allowed hosts with additional validation"""
        allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
        
        # Add localhost and 127.0.0.1 for development if DEBUG is True
        if getattr(settings, 'DEBUG', False):
            development_hosts = ['localhost', '127.0.0.1', '0.0.0.0']
            allowed_hosts.extend(development_hosts)
        
        # Normalize and deduplicate
        normalized_hosts = set()
        for host in allowed_hosts:
            if host == '*':
                return ['*']
            normalized_hosts.add(host.lower())
            # Add version without port
            normalized_hosts.add(host.split(':')[0].lower())
        
        return list(normalized_hosts)
    
    def _is_suspicious_host(self, host):
        """Check if host appears to be suspicious"""
        suspicious_patterns = [
            'admin',
            'api',
            'test',
            'staging',
            'dev',
            'internal',
            'management',
            'cpanel',
            'webmail',
            'mail',
            'ftp',
        ]
        
        host_lower = host.lower()
        return any(pattern in host_lower for pattern in suspicious_patterns)
    
    def _log_security_event(self, request, host, reason):
        """Log security-related events"""
        client_ip = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        
        logger.warning(
            f"Security Event - Host Validation: {reason} | "
            f"Host: '{host}' | IP: {client_ip} | "
            f"User-Agent: {user_agent} | "
            f"Path: {request.path}"
        )
    
    def process_request(self, request):
        """Enhanced request processing with security logging"""
        host = self._extract_host(request)
        
        # Check if host is empty
        if not host:
            self._log_security_event(request, host, "Empty host header")
            return HttpResponseBadRequest("Host header is required.")
        
        # Check if host is valid
        if not self._is_valid_host(host):
            # Track suspicious hosts
            if self._is_suspicious_host(host):
                self.suspicious_hosts.add(host)
                self._log_security_event(request, host, "Suspicious host pattern")
            else:
                self._log_security_event(request, host, "Invalid host")
            
            return HttpResponseBadRequest(
                "Invalid Host header. Request rejected for security reasons."
            )
        
        return None
    
    def _extract_host(self, request):
        """Extract host from request"""
        host = request.META.get('HTTP_HOST', '')
        
        # Handle X-Forwarded-Host for proxy scenarios
        forwarded_host = request.META.get('HTTP_X_FORWARDED_HOST')
        if forwarded_host:
            host = forwarded_host.split(',')[0].strip()
        
        return host.lower()
    
    def _is_valid_host(self, host):
        """Check if host is valid"""
        if not host:
            return False
        
        if '*' in self.allowed_hosts:
            return True
        
        host_without_port = host.split(':')[0]
        
        # Direct match
        if host in self.allowed_hosts or host_without_port in self.allowed_hosts:
            return True
        
        # Wildcard subdomain match
        for allowed_host in self.allowed_hosts:
            if allowed_host.startswith('*.'):
                domain = allowed_host[2:]
                if host_without_port.endswith('.' + domain) or host_without_port == domain:
                    return True
        
        return False
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SessionExpiryMiddleware(MiddlewareMixin):
    """
    Middleware to handle session expiry and redirect users to login page
    when their session has expired.
    """
    
    def process_request(self, request):
        """
        Check if the session has expired and redirect to login if necessary.
        """
        # Skip session check for login/logout pages and static files
        excluded_paths = [
            reverse('account_login'),
            reverse('account_logout'),
            reverse('account_signup'),
            '/static/',
            '/admin/login/',
        ]
        
        # Check if current path should be excluded
        if any(request.path.startswith(path) for path in excluded_paths):
            return None
        
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Check session expiry timestamp
            if 'session_start_time' in request.session:
                try:
                    # Convert stored timestamp (float) back to datetime
                    from datetime import datetime as dt
                    session_start_time = dt.fromtimestamp(request.session['session_start_time'])
                    session_age = (timezone.now() - session_start_time.replace(tzinfo=timezone.utc)).total_seconds()
                except (ValueError, TypeError):
                    # If conversion fails, treat as expired
                    session_age = float('inf')
                
                session_timeout = getattr(settings, 'SESSION_COOKIE_AGE', 3600)
                
                # If session has expired, log out the user
                if session_age > session_timeout:
                    # Clear the session
                    request.session.flush()
                    
                    # Log the session expiry
                    logger.info(
                        f"Session expired for user: {request.user.username} "
                        f"(Session age: {session_age}s, Timeout: {session_timeout}s)"
                    )
                    
                    # Redirect to login page with a message
                    return HttpResponseRedirect(reverse('account_login'))
            else:
                # Set session start time as timestamp (float) instead of datetime object
                # This ensures JSON serialization compatibility
                import time
                request.session['session_start_time'] = time.time()
        
        return None