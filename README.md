# Lab Management System

A Django-based web application for managing computer labs at Taita Taveta University's School of Science and Informatics.

## 🚀 Key Features
- **User Authentication:** Custom roles (Admin, Lecturer, Student) with secure login/signup via Django Allauth and role-based access control.
- **Booking Management:** Resource booking for labs/computers with slot availability, booking creation/deletion, and role-specific views.
- **Notifications:** Real-time updates using Django Notifications HQ with optional email alerts.
- **Support Ticketing:** Create, track, and manage support tickets with priority levels and admin notifications.

## 📦 Installation

### Option A — Docker (recommended)
1. **Clone the Repository:**
   ```bash
   git clone https://github.com/your-username/lab-management-system.git
   cd lab-management-system
   ```
2. **Configure Environment Variables:**
   ```bash
   cp .env.example .env
   # Edit .env and set DJANGO_SECRET_KEY and other values
   ```
3. **Build and Start Containers:**
   ```bash
   make build
   make up
   ```
4. **Apply Migrations & Collect Static Files:**
   ```bash
   make migrate
   make collectstatic
   ```
5. **Login to the Container:**
   ```bash
   make login
   ```

### Option B — Local Development
1. **Clone the Repository:**
   ```bash
   git clone https://github.com/your-username/lab-management-system.git
   cd lab-management-system
   ```
2. **Create Virtual Environment:**
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```
3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Apply Migrations:**
   ```bash
   python manage.py migrate
   ```
5. **Run the Server:**
   ```bash
   python manage.py runserver
   ```

## 🐳 Docker Commands

| Command              | Description                              |
|----------------------|------------------------------------------|
| `make build`         | Build Docker images                      |
| `make up`            | Start all containers in detached mode    |
| `make down`          | Stop and remove all containers           |
| `make restart`       | Restart all containers                   |
| `make login`         | Open a shell inside the web container    |
| `make migrate`       | Run Django database migrations           |
| `make collectstatic` | Collect static files                     |
| `make logs`          | Tail logs for all containers             |

## ⚙️ Usage
- Register and log in with the appropriate role.
- Book lab slots, manage resources, and create support tickets.
- Admins can manage users, view reports, and handle support requests.

## 📧 Contact
For inquiries or support, reach out at [henryoayub15@gmail.com].