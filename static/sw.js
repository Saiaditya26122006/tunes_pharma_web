self.addEventListener('push', function(event) {
    if (event.data) {
        let payload = {};
        try {
            payload = event.data.json();
        } catch (e) {
            payload = { title: 'New Notification', body: event.data.text() };
        }
        
        const title = payload.title || 'New Notification from Tunes Pharma';
        const options = {
            body: payload.body || 'You have a new update.',
            icon: '/static/images/logo.png', // Assuming a logo exists
            badge: '/static/images/logo.png',
            vibrate: [100, 50, 100],
            data: {
                url: payload.url || '/'
            }
        };
        
        event.waitUntil(self.registration.showNotification(title, options));
    }
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    if (event.notification.data && event.notification.data.url) {
        event.waitUntil(clients.openWindow(event.notification.data.url));
    }
});
