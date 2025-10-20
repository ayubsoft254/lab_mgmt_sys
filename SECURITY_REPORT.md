# Lab Management System - Security Report
**Generated: October 20, 2025**

---

## Executive Summary

This document outlines the comprehensive security measures implemented in the Lab Management System (LABMS) - a Django-based web application for managing computer laboratories at Taita Taveta University. The system has been designed with a defense-in-depth approach, incorporating multiple layers of security controls across authentication, authorization, data protection, and application-level security.

---

## 1. Authentication & Authorization Security

### 1.1 User Authentication Framework
- **Framework**: Django Allauth with custom authentication backends
- **Methods**: Email and username-based authentication
- **Email Verification**: Mandatory email verification required for all new accounts
- **Login by Code**: Optional login-by-code feature enabled for enhanced security
- **Custom Account Adapter**: `CustomAccountAdapter` in `booking/adapters.py` implements:
  - Role-based user assignment on registration
  - Email domain validation to prevent unauthorized access

### 1.2 Email Domain Whitelisting
**Location**: `booking/adapters.py` and `booking/forms.py`

The system enforces institutional email-only registration:
- **Students**: Must register with `@students.ttu.ac.ke` domain
- **Lecturers**: Must register with `@ttu.ac.ke` domain
- **Benefit**: Prevents unauthorized external user registration
- **Validation Level**: Applied at both adapter and form levels for redundancy

**Code Implementation**:
```python
allowed_domains = {
    'student': '@students.ttu.ac.ke',
    'lecturer': '@ttu.ac.ke',
}
```

### 1.3 Role-Based Access Control (RBAC)
**User Role Hierarchy**:
- **Super Admin** (`is_super_admin`): Full system access, user management
- **Admin** (`is_admin`): Lab management, booking approvals, user oversight
- **Lecturer** (`is_lecturer`): Lab session scheduling, attendance tracking
- **Student** (`is_student`): Computer booking, session participation

**Enforcement**: 
- View-level decorators: `@login_required`, `@user_passes_test`
- Model-level permissions for sensitive operations
- Example from `booking/views.py`:
```python
@login_required
def admin_dashboard_view(request):
    # Dashboard access restricted to authenticated users
```

### 1.4 Custom User Model
**Location**: `booking/models.py`

Extended Django's `AbstractUser` with:
- Custom authentication fields for role management
- Institutional email requirements
- Profile information (school, course, salutation)
- Lab admin assignments via `managed_labs` ManyToMany field

---

## 2. Session Management Security

### 2.1 Session Configuration
**Location**: `src/settings.py`

```python
SESSION_COOKIE_AGE = 7200  # 2 hours timeout
SESSION_SAVE_EVERY_REQUEST = True  # Update on each request
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Expire on browser close
SESSION_COOKIE_HTTPONLY = True  # Prevent XSS access
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
```

**Security Benefits**:
- **Short timeout**: 2-hour maximum session duration
- **HTTPOnly flag**: Prevents JavaScript from accessing cookies (XSS mitigation)
- **Secure flag**: Ensures cookies sent over HTTPS only
- **SameSite**: Protects against CSRF attacks

### 2.2 Custom Session Expiry Middleware
**Location**: `src/middleware.py` - `SessionExpiryMiddleware` class

**Features**:
- Tracks session start time
- Automatically logs out users after 2-hour timeout
- Graceful redirection to login page with notification
- Excludes public pages (login, signup, static files)
- Handles datetime serialization safely

**Key Security Logic**:
```python
if session_age > session_timeout:
    request.session.flush()  # Clear session
    return HttpResponseRedirect(reverse('account_login'))
```

### 2.3 Custom Serializer
**Location**: `src/serializers.py`

`DateTimeAwareJSONSerializer` provides:
- Proper datetime object serialization
- JSON-safe session data storage
- Prevents serialization vulnerabilities

---

## 3. Cross-Site Request Forgery (CSRF) Protection

### 3.1 CSRF Middleware & Tokens
**Location**: `src/settings.py`

```python
CSRF_COOKIE_SECURE = True  # HTTPS only
CSRF_COOKIE_SAMESITE = 'Lax'  # SameSite protection
CSRF_TRUSTED_ORIGINS = config("TRUSTED_CSRF_ORIGINS", ...)
```

**Enforcement**:
- Django's CSRF middleware enabled: `'django.middleware.csrf.CsrfViewMiddleware'`
- All POST/PUT/DELETE requests require CSRF tokens
- Tokens embedded in all forms using Django template tags

### 3.2 Trusted Origins
Configuration allows only pre-approved domains for cross-origin requests:
- Environment variable: `TRUSTED_CSRF_ORIGINS`
- Prevents CSRF attacks from untrusted domains

---

## 4. Host Header Validation

### 4.1 Custom Host Validation Middleware
**Location**: `src/middleware.py` - `HostValidationMiddleware` class

**Purpose**: Prevent HTTP Host header attacks and cache poisoning

**Features**:
- Validates incoming `HTTP_HOST` header against `ALLOWED_HOSTS`
- Handles proxy scenarios (`X-Forwarded-Host`)
- Supports wildcard subdomains
- Case-insensitive comparison
- Returns `400 Bad Request` for invalid hosts

**Implementation Flow**:
```
1. Extract host from HTTP_HOST or X-Forwarded-Host
2. Normalize to lowercase
3. Compare against ALLOWED_HOSTS list
4. Log security violations
5. Block requests with invalid hosts
```

### 4.2 Enhanced Host Validation
**Location**: `src/middleware.py` - `EnhancedHostValidationMiddleware` class

**Additional Security**:
- Tracks suspicious host patterns (admin, api, staging, cpanel, etc.)
- Logs security events with IP and user-agent info
- Special handling for development mode
- Comprehensive security event logging

**Suspicious Patterns Detected**:
```python
'admin', 'api', 'test', 'staging', 'dev', 'internal', 
'management', 'cpanel', 'webmail', 'mail', 'ftp'
```

### 4.3 Middleware Stack Order
**Location**: `src/settings.py`

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',  # Django's built-in
    'src.middleware.HostValidationMiddleware',  # Custom host validation
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # CSRF protection
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'src.middleware.SessionExpiryMiddleware',  # Custom session expiry
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # Clickjacking protection
]
```

---

## 5. HTTPS & Secure Transport

### 5.1 SSL/TLS Configuration
**Location**: `src/settings.py`

```python
SECURE_SSL_REDIRECT = True  # Force HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

**Benefits**:
- All HTTP connections redirected to HTTPS
- Prevents man-in-the-middle attacks
- Protects sensitive data in transit
- Supports reverse proxy scenarios

### 5.2 Email Encryption
**Configuration**:
```python
EMAIL_USE_TLS = True  # Encrypted email transport
EMAIL_PORT = 587  # TLS standard port
```

---

## 6. Password Security

### 6.1 Password Validators
**Location**: `src/settings.py`

Django's built-in password validation ensures strong passwords:

```python
AUTH_PASSWORD_VALIDATORS = [
    'UserAttributeSimilarityValidator',  # Check against user attributes
    'MinimumLengthValidator',  # Minimum 8 characters
    'CommonPasswordValidator',  # Reject common passwords
    'NumericPasswordValidator',  # Reject all-numeric passwords
]
```

**Security Measures**:
- ✓ Prevents passwords similar to user attributes
- ✓ Enforces minimum length
- ✓ Blocks known weak passwords from database
- ✓ Rejects numeric-only passwords

### 6.2 Password Storage
- Django's PBKDF2 hashing algorithm (default)
- Salted hashes prevent rainbow table attacks
- Uses `django.contrib.auth.hashers` for secure storage

---

## 7. Input Validation & Sanitization

### 7.1 Form-Level Validation
**Location**: `booking/forms.py`

**ComputerBookingForm**:
- Date/time validation
- Future-date requirement
- Conflict detection with existing bookings
- Lab session overlap prevention
- Comprehensive `clean()` method validation

**LabSessionForm**:
- Time range validation
- Scheduler conflict checking
- Computer booking conflict detection
- Reasonable date range enforcement

**RecurringSessionForm**:
- Start/end date validation
- One-year maximum scheduling limit
- Time range checks

**CustomUserCreationForm**:
- Email uniqueness validation (case-insensitive)
- Password match verification
- Email domain validation per role
- Regex pattern matching for institutional emails

### 7.2 Model-Level Validation
**Location**: `booking/models.py`

```python
def clean(self):
    # Validate business logic at model level
    # Runs before saving to database
```

### 7.3 Template Auto-Escaping
- Django templates auto-escape user input by default
- Prevents XSS (Cross-Site Scripting) attacks
- Safe rendering of user-generated content

---

## 8. Data Protection & Privacy

### 8.1 Email Configuration
**Location**: `src/settings.py`

Multiple email accounts for different purposes:
- `EMAIL_HOST_USER`: Standard email account
- `EMAIL_HOST_USER_ADMISSIONS`: Separate admissions account

**Benefits**: 
- Separation of concerns
- Reduced impact if one email compromised
- Audit trail separation

### 8.2 Admin Notifications
```python
ADMINS = [('Admin user', 'admin@example.com')]
MANAGERS = ADMINS
```

**Function**:
- 500 errors emailed to admins
- Critical issues logged and notified

### 8.3 Secure Configuration Management
**Location**: `src/settings.py`

Uses `python-decouple` library:
```python
SECRET_KEY = config("DJANGO_SECRET_KEY")  # Never hardcoded
DEBUG = config("DJANGO_DEBUG", cast=bool, default=False)
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", cast=str, default=None)
```

**Advantages**:
- Environment-based configuration
- No secrets in version control
- Different configs per environment
- Prevents accidental exposure

### 8.4 Default Security Settings
```python
DEBUG = False  # Production default
SECURE_SSL_REDIRECT = True  # HTTPS enforced
```

---

## 9. Logging & Monitoring

### 9.1 Security Event Logging
**Location**: `src/settings.py`

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'security.log',
        },
    },
    'loggers': {
        'src.middleware': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
        },
    },
}
```

**Logged Events**:
- Invalid host headers
- Suspicious host patterns
- Session expiries
- Authentication failures
- Permission denials

### 9.2 Log Location
- **Directory**: `logs/` (auto-created)
- **File**: `logs/security.log`
- **Format**: Verbose with timestamp, module, PID, TID
- **Level**: WARNING and above

### 9.3 Client IP Tracking
**Function**: `_get_client_ip()` in middleware

```python
def _get_client_ip(self, request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
```

**Handles**:
- Direct connections
- Proxy scenarios
- Load balancer deployments

---

## 10. Clickjacking Protection

### 10.1 X-Frame-Options Header
**Location**: `src/settings.py`

```python
MIDDLEWARE = [
    ...
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ...
]
```

**Default Behavior**: Django sets `X-Frame-Options: SAMEORIGIN`

**Protection**:
- Prevents embedding in iframes from other sites
- Protects against clickjacking attacks
- Allows same-origin iframe embedding (if needed)

---

## 11. Database Security

### 11.1 Database Configuration
**Location**: `src/settings.py`

```python
DATABASES = {
    'default': config(
        'DATABASE_URL',
        cast=db_url,
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}'
    )
}
```

**Features**:
- Environment-based database URL
- Supports PostgreSQL/MySQL in production
- Default to SQLite for development
- No hardcoded credentials

### 11.2 ORM Parameterized Queries
- Django ORM prevents SQL injection
- All queries use parameterized statements
- User input never directly in SQL

### 11.3 Model Permissions
- Django's permission system integrated
- Custom permissions for sensitive operations
- Admin interface respects permissions

---

## 12. Celery Task Security

### 12.1 Message Broker Security
**Location**: `src/settings.py`

```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
```

**Security Measures**:
- JSON serialization (no pickle vulnerability)
- Local Redis connection
- Restricted content types

### 12.2 Scheduled Tasks
**Celery Beat Schedule**:
- Check ending bookings (every minute)
- Notify admins of pending bookings (every 2 hours)
- Broadcast announcements (hourly)

**All tasks** perform authorization checks before execution

---

## 13. Error Handling & Information Disclosure

### 13.1 Custom Error Handlers
**Location**: `src/views.py` and URL configuration

Custom error pages prevent information leakage:
- `400.html` - Bad Request
- `403.html` - Permission Denied
- `404.html` - Not Found
- `500.html` - Server Error

**Benefits**:
- No stack traces in production
- Consistent error experience
- Request IDs for debugging (UUID truncated to 8 chars)
- Professional appearance

### 13.2 Error Logging
- Stack traces logged server-side
- Only safe error messages shown to users
- Admin notifications for critical errors

---

## 14. Third-Party Dependencies Security

### 14.1 Core Security Dependencies
**Location**: `requirements.txt`

| Package | Version | Purpose |
|---------|---------|---------|
| Django | 5.1.7 | Web framework with security features |
| django-allauth | 65.7.0 | Authentication with email verification |
| PyJWT | 2.10.1 | JWT token handling |
| cryptography | 44.0.2 | Cryptographic operations |
| requests | 2.32.3 | HTTP library with security defaults |
| python-decouple | 3.8 | Secure configuration management |

### 14.2 Dependency Management
- Regular updates via requirements.txt
- Version pinning for stability
- All major security packages up-to-date

---

## 15. API Security

### 15.1 JSON Response Serialization
**Location**: `src/json_encoders.py`, `src/serializers.py`

Custom JSON encoders handle:
- Datetime serialization safely
- Decimal precision for financial data
- UUID encoding
- Prevents serialization vulnerabilities

### 15.2 API Endpoint Protection
All API endpoints require:
- Authentication (`@login_required`)
- CSRF tokens for mutations
- Role-based authorization
- Input validation

**Example API Endpoints**:
```python
path('api/sessions/<int:session_id>/details/', views.session_details_api)
path('api/bookings/<int:booking_id>/details/', views.booking_details_api)
path('api/students/<int:student_id>/bookings/', views.student_bookings_api)
```

---

## 16. Booking & Session Security

### 16.1 Conflict Prevention
**Implemented Checks**:
- ✓ Double-booking prevention
- ✓ Lab session overlap detection
- ✓ Computer availability verification
- ✓ Time range validation
- ✓ Future-date requirement

### 16.2 Approval Workflow
- Student bookings require admin approval
- Lecturer sessions require admin approval
- Prevents unauthorized lab usage
- Audit trail of approvals

### 16.3 Access Control
- Students can only view/modify their own bookings
- Lecturers can only view/modify their own sessions
- Admins have oversight of all bookings
- Proper authorization checks on all views

---

## 17. Compliance & Best Practices

### 17.1 Django Security Best Practices
✓ Using Django 5.1.7 (latest stable)
✓ HTTPS enforcement enabled
✓ CSRF protection enabled
✓ XSS protection (template auto-escape)
✓ SQL injection prevention (ORM)
✓ Clickjacking protection
✓ Secure headers configured
✓ Session security hardened

### 17.2 Security Middleware Stack
1. **SecurityMiddleware** - Django's built-in security headers
2. **HostValidationMiddleware** - Host header validation
3. **SessionMiddleware** - Session management
4. **CsrfViewMiddleware** - CSRF protection
5. **AuthenticationMiddleware** - User authentication
6. **SessionExpiryMiddleware** - Session timeout
7. **XFrameOptionsMiddleware** - Clickjacking protection

### 17.3 Configuration Checklist
- ✓ SECRET_KEY from environment
- ✓ DEBUG set to False in production
- ✓ ALLOWED_HOSTS configured
- ✓ SECURE_SSL_REDIRECT enabled
- ✓ SESSION cookies secure and HTTPOnly
- ✓ CSRF cookies secure
- ✓ Email credentials from environment
- ✓ Database credentials from environment
- ✓ Logging configured for security events

---

## 18. Recommendations for Enhanced Security

### 18.1 Short-Term Improvements
1. **Multi-Factor Authentication (MFA)**
   - Add TOTP support for admin users
   - Consider email-based 2FA for all users

2. **Rate Limiting**
   - Implement rate limiting on login endpoints
   - Prevent brute-force password attacks

3. **Password Reset Security**
   - Token expiration on password reset links
   - One-time use tokens

4. **API Authentication**
   - Consider API keys for integrations
   - JWT tokens with short expiration

### 18.2 Medium-Term Improvements
1. **Security Headers**
   - Add Content-Security-Policy (CSP)
   - Add X-Content-Type-Options: nosniff
   - Add X-XSS-Protection header

2. **Audit Logging**
   - Enhanced audit trail for sensitive operations
   - User activity tracking
   - Booking history immutability

3. **Data Encryption**
   - Encrypt sensitive fields at rest
   - PII field encryption (email, names)

4. **Security Scanning**
   - Integrate SAST (Static Application Security Testing)
   - Regular dependency vulnerability scans
   - Penetration testing

### 18.3 Long-Term Improvements
1. **Zero-Trust Architecture**
   - Implement network segmentation
   - Service-to-service authentication

2. **Enhanced Monitoring**
   - SIEM integration
   - Real-time security alerts
   - Anomaly detection

3. **Disaster Recovery**
   - Regular backups with encryption
   - Disaster recovery plan
   - Business continuity testing

4. **Compliance**
   - GDPR compliance measures
   - Data retention policies
   - Privacy impact assessment

---

## 19. Security Testing Checklist

### 19.1 Manual Testing
- [ ] Test invalid host header rejection
- [ ] Verify session expiry after 2 hours
- [ ] Confirm CSRF token requirement
- [ ] Test role-based access control
- [ ] Verify email domain validation
- [ ] Test booking conflict prevention

### 19.2 Automated Testing
- [ ] Security middleware unit tests
- [ ] Form validation tests
- [ ] Permission decorator tests
- [ ] Session expiry tests
- [ ] CSRF token tests

### 19.3 Penetration Testing Areas
- Authentication bypass attempts
- Authorization vulnerabilities
- SQL injection attempts
- XSS attack vectors
- CSRF attack scenarios
- Session hijacking attempts

---

## 20. Security Incident Response

### 20.1 Logging Enabled For
- Invalid host headers
- Session expirations
- Authentication failures
- Permission denials
- Server errors (500s)

### 20.2 Admin Notifications
- Critical errors email admins
- Configured via `ADMINS` setting
- Immediate alerting of issues

### 20.3 Log Access
- **Location**: `logs/security.log`
- **Format**: Verbose with timestamps
- **Retention**: Monitor and archive regularly
- **Analysis**: Review weekly for patterns

---

## Conclusion

The Lab Management System implements a comprehensive, multi-layered security architecture that addresses:

1. ✅ **Authentication & Authorization** - Role-based access with email verification
2. ✅ **Data Protection** - Secure configuration and transport
3. ✅ **Session Management** - Timeout and secure cookie handling
4. ✅ **CSRF Protection** - Token-based defense
5. ✅ **Host Header Validation** - Attack prevention
6. ✅ **Input Validation** - Form and model-level checks
7. ✅ **HTTPS Enforcement** - Encrypted transport
8. ✅ **Error Handling** - Information disclosure prevention
9. ✅ **Logging & Monitoring** - Security event tracking
10. ✅ **Third-Party Dependencies** - Latest secure versions

**Overall Security Posture**: **GOOD**

The system demonstrates solid security fundamentals with Django best practices applied throughout. Recommended next steps include implementing rate limiting, enhanced audit logging, and security header additions as outlined in section 18.

---

## Document Information

- **Last Updated**: October 20, 2025
- **Prepared By**: Security Audit
- **Scope**: Lab Management System (LABMS)
- **Framework Version**: Django 5.1.7
- **Review Schedule**: Quarterly
- **Next Review**: January 2026

---
