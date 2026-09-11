// Enregistrement du service worker (PWA). Le SW est servi à la racine ("/service-worker.js")
// pour que son scope couvre toute l'app (les fichiers sous /static/ auraient un scope trop restreint).
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/service-worker.js').catch((err) => {
            console.warn('Service worker registration failed:', err);
        });
    });
}
