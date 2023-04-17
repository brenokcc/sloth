'use strict';

self.addEventListener('push', function (event) {
    console.log('[Service Worker] Push Received.');
    console.log(`[Service Worker] Push had this data: "${event.data.text()}"`);

    const title = 'Hello World!';
    const options = {
        body: event.data.text(),
        icon: '/static/images/images/icon.png',
        badge: '/static/images/images/badge.png'
    };

    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function (event) {
    console.log('[Service Worker] Notification click Received.');
    event.notification.close();
    //event.waitUntil(clients.openWindow('http://petshop.aplicativo.click/app/login/'));
});

