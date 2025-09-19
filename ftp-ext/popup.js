// DOM elements
const loginSection = document.getElementById('loginSection');
const registerSection = document.getElementById('registerSection');
const mainSection = document.getElementById('mainSection');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const regUsernameInput = document.getElementById('regUsername');
const regEmailInput = document.getElementById('regEmail');
const regPasswordInput = document.getElementById('regPassword');
const regPasswordConfirmInput = document.getElementById('regPasswordConfirm');
const showRegisterBtn = document.getElementById('showRegisterBtn');
const showLoginBtn = document.getElementById('showLoginBtn');
const welcomeMessage = document.getElementById('welcomeMessage');
const logoutBtn = document.getElementById('logoutBtn');
const openWebInterfaceBtn = document.getElementById('openWebInterfaceBtn');
const refreshLogsBtn = document.getElementById('refreshLogsBtn');
const transferList = document.getElementById('transferList');
const errorMessage = document.getElementById('errorMessage');
const successMessage = document.getElementById('successMessage');

// API base URL - Use Replit domain for production
const API_BASE_URL = 'https://b381e644-e640-45f5-b15f-3d16ece2bc4b-00-1rte04lb9mmp4.sisko.replit.dev';

// Initialize popup
document.addEventListener('DOMContentLoaded', async () => {
    await checkAuthStatus();
    setupEventListeners();
});

// Check if user is already authenticated
async function checkAuthStatus() {
    try {
        const result = await chrome.storage.local.get(['authToken', 'username']);
        if (result.authToken && result.username) {
            // Verify token with server
            const response = await fetch(`${API_BASE_URL}/api/verify-token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${result.authToken}`
                }
            });
            
            if (response.ok) {
                showMainSection(result.username);
                await loadRecentTransfers();
            } else {
                // Token expired or invalid
                await chrome.storage.local.remove(['authToken', 'username']);
                showLoginSection();
            }
        } else {
            showLoginSection();
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        showError('Failed to verify authentication status');
        showLoginSection();
    }
}

// Setup event listeners
function setupEventListeners() {
    loginForm.addEventListener('submit', handleLogin);
    registerForm.addEventListener('submit', handleRegister);
    showRegisterBtn.addEventListener('click', showRegisterSection);
    showLoginBtn.addEventListener('click', showLoginSection);
    logoutBtn.addEventListener('click', handleLogout);
    openWebInterfaceBtn.addEventListener('click', openWebInterface);
    refreshLogsBtn.addEventListener('click', loadRecentTransfers);
}

// Handle login form submission
async function handleLogin(event) {
    event.preventDefault();
    
    const username = usernameInput.value.trim();
    const password = passwordInput.value;
    
    if (!username || !password) {
        showError('Please enter both username and password');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Store auth token and username
            await chrome.storage.local.set({
                authToken: data.token,
                username: username
            });
            
            showSuccess('Login successful!');
            setTimeout(() => {
                showMainSection(username);
                loadRecentTransfers();
            }, 1000);
        } else {
            showError(data.error || 'Login failed');
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('Failed to connect to server. Please ensure the server is running.');
    }
}

// Handle registration form submission
async function handleRegister(event) {
    event.preventDefault();
    
    const username = regUsernameInput.value.trim();
    const email = regEmailInput.value.trim();
    const password = regPasswordInput.value;
    const confirmPassword = regPasswordConfirmInput.value;
    
    if (!username || !password) {
        showError('Please enter both username and password');
        return;
    }
    
    if (password.length < 8) {
        showError('Password must be at least 8 characters long');
        return;
    }
    
    if (password !== confirmPassword) {
        showError('Passwords do not match');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccess('Registration successful! Please login.');
            setTimeout(() => {
                showLoginSection();
                usernameInput.value = username; // Pre-fill username
            }, 1500);
        } else {
            showError(data.error || 'Registration failed');
        }
    } catch (error) {
        console.error('Registration error:', error);
        showError('Failed to connect to server. Please ensure the server is running.');
    }
}

// Handle logout
async function handleLogout() {
    try {
        const result = await chrome.storage.local.get(['authToken']);
        if (result.authToken) {
            // Notify server about logout
            await fetch(`${API_BASE_URL}/api/logout`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${result.authToken}`
                }
            });
        }
        
        // Clear local storage
        await chrome.storage.local.remove(['authToken', 'username']);
        showLoginSection();
        showSuccess('Logged out successfully');
    } catch (error) {
        console.error('Logout error:', error);
        // Still clear local storage even if server request fails
        await chrome.storage.local.remove(['authToken', 'username']);
        showLoginSection();
    }
}

// Open web interface in new tab
function openWebInterface() {
    chrome.tabs.create({ url: API_BASE_URL });
}

// Load recent transfers
async function loadRecentTransfers() {
    try {
        const result = await chrome.storage.local.get(['authToken']);
        if (!result.authToken) return;
        
        const response = await fetch(`${API_BASE_URL}/api/recent-transfers`, {
            headers: {
                'Authorization': `Bearer ${result.authToken}`
            }
        });
        
        if (response.ok) {
            const transfers = await response.json();
            displayTransfers(transfers);
        } else {
            console.error('Failed to load transfers');
        }
    } catch (error) {
        console.error('Error loading transfers:', error);
    }
}

// Display transfers in the list
function displayTransfers(transfers) {
    if (!transfers || transfers.length === 0) {
        transferList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>No recent transfers</p>
            </div>
        `;
        return;
    }
    
    transferList.innerHTML = transfers.map(transfer => `
        <div class="transfer-item">
            <div class="filename">
                <i class="fas ${transfer.type === 'upload' ? 'fa-upload' : 'fa-download'}"></i>
                ${transfer.filename}
            </div>
            <div class="details">
                <span>${transfer.size}</span>
                <span>${new Date(transfer.timestamp).toLocaleString()}</span>
            </div>
        </div>
    `).join('');
}

// Show main section
function showMainSection(username) {
    loginSection.classList.add('hidden');
    mainSection.classList.remove('hidden');
    welcomeMessage.textContent = `Welcome, ${username}`;
    clearMessages();
}

// Show login section
function showLoginSection() {
    mainSection.classList.add('hidden');
    registerSection.classList.add('hidden');
    loginSection.classList.remove('hidden');
    loginForm.reset();
    clearMessages();
}

// Show registration section
function showRegisterSection() {
    loginSection.classList.add('hidden');
    mainSection.classList.add('hidden');
    registerSection.classList.remove('hidden');
    registerForm.reset();
    clearMessages();
}

// Show error message
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
    successMessage.classList.add('hidden');
    setTimeout(clearMessages, 5000);
}

// Show success message
function showSuccess(message) {
    successMessage.textContent = message;
    successMessage.classList.remove('hidden');
    errorMessage.classList.add('hidden');
    setTimeout(clearMessages, 3000);
}

// Clear all messages
function clearMessages() {
    errorMessage.classList.add('hidden');
    successMessage.classList.add('hidden');
}
