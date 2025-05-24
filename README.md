Lab Management System

<img alt="Django" src="https://img.shields.io/badge/Django-4.2-green.svg">
<img alt="Python" src="https://img.shields.io/badge/Python-3.10+-blue.svg">
<img alt="License" src="https://img.shields.io/badge/License-MIT-yellow.svg">
A comprehensive Django-based web application designed specifically for managing computer laboratories at Taita Taveta University's School of Science and Informatics. This system facilitates efficient resource allocation, booking management, and lab administration.

🔍 Overview
The Lab Management System (LMS) provides an intuitive platform for students, lecturers, and administrators to coordinate the use of computer labs and equipment. With features like real-time availability tracking, automated notifications, and comprehensive analytics, LMS streamlines the entire lab management workflow.

🚀 Key Features
🔐 User Authentication & Role Management
Multi-Role Support: Distinct user roles (Super Admin, Admin, Lecturer, Student) with tailored permissions
Secure Authentication: Integration with Django Allauth for robust authentication flows
Role-Based Access Control: Restricted access to features based on user role
Profile Management: Customizable user profiles with academic information
📅 Booking & Scheduling
Computer Booking: Individual computer reservations with time-slot selection
Lab Session Management: Full lab reservations for classes and group activities
Recurring Sessions: Schedule repeating lab sessions (daily, weekly, monthly)
Conflict Prevention: Automated checks to prevent double-booking of resources
Real-Time Availability: Visual calendar showing resource availability
📊 Analytics & Reporting
Usage Statistics: Comprehensive data on lab and computer utilization
User Activity Tracking: Monitor booking patterns and resource demands
Performance Metrics: System uptime and resource allocation efficiency
Exportable Reports: Generate PDF and CSV reports for administrative use
🔔 Notifications & Alerts
Real-Time Notifications: In-app alerts for booking approvals, cancellations, and reminders
Session Reminders: Automated alerts when bookings are about to expire
Session Extensions: Option to extend sessions when resources remain available
Email Notifications: Optional email alerts for critical updates
🛠️ Administration Tools
Lab Management: Add, remove, and modify lab configurations
Computer Management: Track individual computer status and specifications
User Management: Admin interface for user role assignment and permissions
System Events: Logging of all significant system activities with severity levels
💬 Support & Communication
Contact System: Direct communication channel between users and administrators
Help Documentation: Integrated guides for system usage
User Ratings: Feedback mechanism to maintain accountability
📦 Installation
Prerequisites
Python 3.10+
pip
Git
Redis (for Celery task queue)
Step-by-Step Installation
Clone the Repository:

Create and Activate Virtual Environment:

Install Dependencies:

Environment Configuration: Create a .env file in the project root with the following variables:

Apply Database Migrations:

Create a Superuser (Admin):

Start the Development Server:

Start Celery for Background Tasks (Optional):

💻 Usage Guide
For Students
Register/login with student credentials
Browse available computers/labs and check the schedule
Book a computer for individual use
View and manage your bookings
Receive notifications before session expiration
Request session extensions when available
For Lecturers
Login with lecturer credentials
Schedule lab sessions for classes
Create recurring sessions for regular classes
View and manage booked sessions
Track student attendance
For Administrators
Login with admin credentials
Manage users, labs, and computers
Approve or reject booking requests
View analytics and generate reports
Configure system settings
Monitor system events and logs
For Super Administrators
Access all administrator features
Manage administrator accounts
Configure global system settings
Access advanced analytics and system performance metrics
🧩 System Architecture
The Lab Management System is built with a modular architecture using Django's app structure:

booking: Core module handling lab and computer bookings
analytics: Data visualization and reporting tools
contact: Communication system for users and administrators
notifications: Real-time alert management system
🧪 Technologies Used
Backend
Django 4.2+: Main web framework
Django REST Framework: API development
Celery: Background task processing
Redis: Message broker for Celery
PostgreSQL/SQLite: Database options
Frontend
TailwindCSS: Utility-first CSS framework
Alpine.js: Lightweight JavaScript framework
Chart.js: Interactive data visualization
htmx: AJAX capabilities without writing JavaScript
DevOps & Tools
Docker: Containerization (optional)
Git: Version control
GitHub Actions: CI/CD pipelines
pytest: Comprehensive testing framework
🤝 Contributing
Contributions are welcome! Please follow these steps:

Fork the repository
Create a feature branch: git checkout -b feature/amazing-feature
Commit your changes: git commit -m 'Add some amazing feature'
Push to the branch: git push origin feature/amazing-feature
Open a pull request
Please ensure your code follows the project's style guidelines and includes appropriate tests.

📝 License
This project is licensed under the MIT License - see the LICENSE file for details.

📊 Project Status
This project is actively maintained and regularly updated with new features and bug fixes.

📧 Contact
For questions, support, or collaboration:

Email: henryoayub15@gmail.com
Built with ❤️ for Taita Taveta University's School of Science and Informatics