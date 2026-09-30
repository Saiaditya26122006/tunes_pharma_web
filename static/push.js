// Notification logic for Doctor Portal
const publicVapidKey = 'REPLACE_WITH_VAPID_PUBLIC_KEY'; // To be replaced in production

async function subscribeUserToPush() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.warn('Push messaging is not supported');
        return false;
    }
    
    try {
        const registration = await navigator.serviceWorker.register('/static/sw.js');
        
        // Ensure VAPID key is configured before subscribing
        if (publicVapidKey.includes('REPLACE')) {
            console.warn('VAPID public key not configured.');
            return false;
        }

        const subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(publicVapidKey)
        });
        
        // Send subscription to server
        await fetch('/api/push-subscribe', {
            method: 'POST',
            body: JSON.stringify(subscription),
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        return true;
    } catch (err) {
        console.error('Failed to subscribe to push notifications:', err);
        return false;
    }
}

function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// Preference management
async function updatePreferences(prefs) {
    try {
        const res = await fetch('/api/doctor/preferences', {
            method: 'POST',
            body: JSON.stringify(prefs),
            headers: {
                'Content-Type': 'application/json'
            }
        });
        const data = await res.json();
        if (data.success && prefs.push) {
            // Attempt to subscribe if push is enabled
            await subscribeUserToPush();
        }
        return data.success;
    } catch (e) {
        console.error("Error updating preferences", e);
        return false;
    }
}
