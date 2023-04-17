const applicationServerPublicKey = 'BLoLJSopQbe04v_zpegJmayhH2Px0EGzrFIlM0OedSOTYsMpO5YGmHOxbpPXdM09ttIuDaDTI86uC85JXZPpEtA';
let swRegistration = null;
function urlB64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}
if ('serviceWorker' in navigator && 'PushManager' in window) {
    //console.log('Service Worker and Push is supported');
    navigator.serviceWorker.register('/static/js/sw.js')
        .then(function (swRegistration) {
            console.log('Service Worker is registered');
            const applicationServerKey = urlB64ToUint8Array(applicationServerPublicKey);
            swRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: applicationServerKey
            }).then(function (subscription) {
                console.log(subscription);
                subscriptionJson = JSON.stringify(subscription);
                console.log(subscriptionJson);
                if (subscription) {
                    console.log('inscrito');
                } else {
                    console.log('não inscrito');
                }
                $.post('/app/dashboard/notification_subscribe/', {csrfmiddlewaretoken: '{{ csrf_token }}', subscription: subscriptionJson}, function(data){

                 });
            }).catch(function (err) {
                //console.log('Failed to subscribe the user: ', err);
            });
        })
        .catch(function (error) {
            console.error('Service Worker Error', error);
        });
} else {
    console.warn('Push messaging is not supported');
}