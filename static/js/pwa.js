// Vinicius PWA Installation & Lifecycle Logic
let deferredPrompt;

// Capture the install prompt event
window.addEventListener('beforeinstallprompt', (e) => {
    // Prevent the mini-infobar from appearing on mobile
    e.preventDefault();
    // Stash the event so it can be triggered later.
    deferredPrompt = e;
    console.log('Vinicius Command: Install prompt captured');
    
    // Notify the UI that the install button can be shown
    window.dispatchEvent(new CustomEvent('pwa-installable'));
});

// Function to trigger installation
async function installPWA() {
    if (!deferredPrompt) {
        console.log('Vinicius Command: Install prompt not available yet');
        return;
    }
    // Show the install prompt
    deferredPrompt.prompt();
    // Wait for the user to respond to the prompt
    const { outcome } = await deferredPrompt.userChoice;
    console.log(`Vinicius Command: User response to the install prompt: ${outcome}`);
    // We've used the prompt, and can't use it again, throw it away
    deferredPrompt = null;
}

// Track installation status
window.addEventListener('appinstalled', (event) => {
    console.log('Vinicius Command: App successfully installed to home screen');
    // Hide the install buttons globally
    document.querySelectorAll('.pwa-install-btn').forEach(btn => btn.style.display = 'none');
});

// Check if running in standalone mode
function isStandalone() {
    return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
}

// Global lifecycle initializations
document.addEventListener('DOMContentLoaded', () => {
    if (isStandalone()) {
        console.log('Vinicius Command: Running in standalone mode');
        document.body.classList.add('pwa-mode');
    }
});
