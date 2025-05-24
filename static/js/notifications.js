function initNotifications() {
    // Check browser support for notifications
    if (!("Notification" in window)) {
        console.log("This browser does not support desktop notification");
        return;
    }
    
    // Request permission
    if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
        Notification.requestPermission();
    }
    
    // Start polling for new notifications
    checkNewNotifications();
}

function checkNewNotifications() {
    // Poll server for new notifications every 30 seconds
    setInterval(() => {
        fetch('/notifications/unread/json/')
            .then(response => response.json())
            .then(data => {
                if (data.count > 0) {
                    // We have new notifications
                    data.notifications.forEach(notification => {
                        if (notification.notification_type === 'booking_ending') {
                            showBrowserNotification(
                                'Booking Ending Soon', 
                                notification.message, 
                                '/notifications/' + notification.id + '/'
                            );
                        }
                    });
                    
                    // Update notification count in the UI
                    updateNotificationBadge(data.count);
                }
            });
    }, 30000);
}

function showBrowserNotification(title, body, url) {
    if (Notification.permission === "granted") {
        const notification = new Notification(title, {
            body: body,
            icon: '/static/images/logo.png'
        });
        
        notification.onclick = function() {
            window.open(url, '_blank');
        };
    }
}

function updateNotificationBadge(count) {
    const badge = document.querySelector('.notification-badge');
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'flex' : 'none';
    }
}

// Initialize when the page loads
document.addEventListener('DOMContentLoaded', initNotifications);