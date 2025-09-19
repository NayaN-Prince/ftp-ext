// Content script for enhanced web interface functionality
(function() {
    'use strict';
    
    // Only run on the web interface pages
    if (!window.location.href.includes('b381e644-e640-45f5-b15f-3d16ece2bc4b-00-1rte04lb9mmp4.sisko.replit.dev')) {
        return;
    }
    
    console.log('SFTP Extension content script loaded');
    
    // Add extension integration functionality
    function addExtensionIntegration() {
        // Check if we're on the main interface page
        const uploadArea = document.querySelector('.upload-area');
        if (!uploadArea) return;
        
        // Add extension indicator
        const extensionIndicator = document.createElement('div');
        extensionIndicator.className = 'extension-indicator';
        extensionIndicator.innerHTML = `
            <div class="indicator-content">
                <i class="fas fa-puzzle-piece"></i>
                <span>Chrome Extension Active</span>
            </div>
        `;
        extensionIndicator.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 12px;
            border-radius: 20px;
            font-size: 12px;
            z-index: 10000;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        `;
        
        document.body.appendChild(extensionIndicator);
        
        // Fade out after 3 seconds
        setTimeout(() => {
            extensionIndicator.style.opacity = '0.3';
        }, 3000);
    }
    
    // Enhance file upload with extension features
    function enhanceFileUpload() {
        const uploadButtons = document.querySelectorAll('input[type="file"]');
        uploadButtons.forEach(button => {
            button.addEventListener('change', function(e) {
                const files = Array.from(e.target.files);
                console.log('Files selected via extension:', files.map(f => f.name));
                
                // Notify extension about file selection
                chrome.runtime.sendMessage({
                    action: 'filesSelected',
                    files: files.map(f => ({
                        name: f.name,
                        size: f.size,
                        type: f.type
                    }))
                }, response => {
                    if (chrome.runtime.lastError) {
                        console.log('Extension communication failed');
                    }
                });
            });
        });
    }
    
    // Add keyboard shortcuts
    function addKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // Ctrl+U for upload
            if (e.ctrlKey && e.key === 'u') {
                e.preventDefault();
                const uploadInput = document.querySelector('input[type="file"]');
                if (uploadInput) {
                    uploadInput.click();
                }
            }
            
            // Ctrl+R for refresh transfers
            if (e.ctrlKey && e.key === 'r') {
                e.preventDefault();
                const refreshBtn = document.querySelector('.refresh-btn');
                if (refreshBtn) {
                    refreshBtn.click();
                }
            }
        });
    }
    
    // Initialize enhancements when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeEnhancements);
    } else {
        initializeEnhancements();
    }
    
    function initializeEnhancements() {
        addExtensionIntegration();
        enhanceFileUpload();
        addKeyboardShortcuts();
        
        // Monitor for dynamic content changes
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList') {
                    enhanceFileUpload();
                }
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
    // Handle messages from background script
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
        if (request.action === 'refreshInterface') {
            location.reload();
        }
        
        if (request.action === 'showNotification') {
            showNotification(request.message, request.type);
        }
    });
    
    // Show in-page notifications
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `extension-notification ${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 50px;
            right: 10px;
            padding: 10px 15px;
            border-radius: 5px;
            color: white;
            font-size: 14px;
            z-index: 10001;
            animation: slideIn 0.3s ease;
            max-width: 300px;
            background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#007bff'};
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 4000);
    }
    
    // Add CSS animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
})();
