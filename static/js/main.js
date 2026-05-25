// DroneDine Shared Utilities – Phase 1
window.DroneDine = window.DroneDine || {};

DroneDine.showToast = function(message, type = 'info') {
    // Simple alert for MVP – replace with a toast later
    alert(`[${type.toUpperCase()}] ${message}`);
};

DroneDine.apiRequest = async function(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        if (!response.ok) throw new Error(await response.text());
        return await response.json();
    } catch (err) {
        DroneDine.showToast(err.message, 'error');
        throw err;
    }
};
