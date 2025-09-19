// Background script for the Chrome extension
chrome.runtime.onInstalled.addListener(() => {
    console.log('Secure SFTP Transfer extension installed');
});

// Handle messages from content scripts or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'checkServerStatus') {
        checkServerStatus()
            .then(status => sendResponse({ status }))
            .catch(error => sendResponse({ status: false, error: error.message }));
        return true; // Keep message channel open for async response
    }
    
    if (request.action === 'openWebInterface') {
        chrome.tabs.create({ url: 'https://b381e644-e640-45f5-b15f-3d16ece2bc4b-00-1rte04lb9mmp4.sisko.replit.dev' });
        sendResponse({ success: true });
    }
});

// Check if the backend server is running
async function checkServerStatus() {
    try {
        const response = await fetch('https://b381e644-e640-45f5-b15f-3d16ece2bc4b-00-1rte04lb9mmp4.sisko.replit.dev/api/health', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        return response.ok;
    } catch (error) {
        console.error('Server health check failed:', error);
        return false;
    }
}

// Periodic server status check
setInterval(async () => {
    const isServerRunning = await checkServerStatus();
    
    // Store server status for use by popup
    chrome.storage.local.set({ serverStatus: isServerRunning });
    
    // Update badge text based on server status
    chrome.action.setBadgeText({
        text: isServerRunning ? '' : '!'
    });
    
    chrome.action.setBadgeBackgroundColor({
        color: '#ff0000'
    });
}, 30000); // Check every 30 seconds

// Handle tab updates to inject content script if needed
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url) {
        // Only inject on Replit domain for development
        if (tab.url.includes('b381e644-e640-45f5-b15f-3d16ece2bc4b-00-1rte04lb9mmp4.sisko.replit.dev')) {
            chrome.scripting.executeScript({
                target: { tabId: tabId },
                files: ['content.js']
            }).catch(console.error);
        }
    }
});
