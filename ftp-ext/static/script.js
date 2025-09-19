// Secure SFTP Transfer Web Interface
class SFTPApp {
    constructor() {
        this.apiBaseUrl = window.location.origin;
        this.authToken = null;
        this.currentUser = null;
        this.uploadQueue = [];
        this.activeTransfers = new Map();
        
        // Debug: Log the API base URL
        console.log('API Base URL:', this.apiBaseUrl);
        console.log('Current location:', window.location);
        
        this.init();
    }
    
    init() {
        this.checkAuthStatus();
        this.setupEventListeners();
        this.setupDragAndDrop();
        this.loadRecentTransfers();
    }
    
    // Authentication Methods
    async checkAuthStatus() {
        const token = localStorage.getItem('authToken');
        const username = localStorage.getItem('username');
        
        if (token && username) {
            try {
                const response = await fetch(`${this.apiBaseUrl}/api/verify-token`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    this.authToken = token;
                    this.currentUser = username;
                    this.showMainInterface();
                    this.loadRecentTransfers();
                } else {
                    this.clearAuth();
                    this.showWelcomeSection();
                }
            } catch (error) {
                console.error('Auth check failed:', error);
                this.clearAuth();
                this.showWelcomeSection();
            }
        } else {
            this.showWelcomeSection();
        }
    }
    
    async login(username, password) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.authToken = data.token;
                this.currentUser = username;
                localStorage.setItem('authToken', data.token);
                localStorage.setItem('username', username);
                
                this.showSuccess('Login successful!');
                this.hideModal('loginModal');
                this.showMainInterface();
                this.loadRecentTransfers();
                
                return true;
            } else {
                this.showError(data.error || 'Login failed');
                return false;
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showError('Failed to connect to server. Please ensure the server is running.');
            return false;
        }
    }
    
    async register(username, email, password) {
        try {
            console.log('Attempting registration to:', `${this.apiBaseUrl}/api/register`);
            const response = await fetch(`${this.apiBaseUrl}/api/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, email, password })
            });
            
            console.log('Registration response status:', response.status);
            const data = await response.json();
            
            if (response.ok) {
                this.showSuccess('Registration successful! Please login.');
                this.hideModal('registerModal');
                this.showModal('loginModal');
                return true;
            } else {
                console.error('Registration failed:', data);
                this.showError(data.error || 'Registration failed');
                return false;
            }
        } catch (error) {
            console.error('Registration error details:', error);
            console.error('Error type:', error.constructor.name);
            console.error('Error message:', error.message);
            this.showError(`Failed to connect to server: ${error.message}`);
            return false;
        }
    }
    
    async logout() {
        try {
            if (this.authToken) {
                await fetch(`${this.apiBaseUrl}/api/logout`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${this.authToken}`
                    }
                });
            }
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            this.clearAuth();
            this.showWelcomeSection();
            this.showSuccess('Logged out successfully');
        }
    }
    
    clearAuth() {
        this.authToken = null;
        this.currentUser = null;
        localStorage.removeItem('authToken');
        localStorage.removeItem('username');
    }
    
    // UI Methods
    showMainInterface() {
        document.getElementById('welcomeSection').classList.add('d-none');
        document.getElementById('mainInterface').classList.remove('d-none');
        document.getElementById('loginNavBtn').classList.add('d-none');
        document.getElementById('userMenu').classList.remove('d-none');
        document.getElementById('navUsername').textContent = this.currentUser;
    }
    
    showWelcomeSection() {
        document.getElementById('welcomeSection').classList.remove('d-none');
        document.getElementById('mainInterface').classList.add('d-none');
        document.getElementById('loginNavBtn').classList.remove('d-none');
        document.getElementById('userMenu').classList.add('d-none');
    }
    
    showModal(modalId) {
        const modal = new bootstrap.Modal(document.getElementById(modalId));
        modal.show();
    }
    
    hideModal(modalId) {
        const modal = bootstrap.Modal.getInstance(document.getElementById(modalId));
        if (modal) {
            modal.hide();
        }
    }
    
    showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toastContainer');
        const toastId = 'toast-' + Date.now();
        
        const toastHtml = `
            <div class="toast" id="${toastId}" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header">
                    <i class="fas fa-${this.getToastIcon(type)} me-2 text-${type}"></i>
                    <strong class="me-auto">Secure SFTP</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
        
        // Remove toast element after it's hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }
    
    getToastIcon(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
    
    showSuccess(message) {
        this.showToast(message, 'success');
    }
    
    showError(message) {
        this.showToast(message, 'error');
    }
    
    showWarning(message) {
        this.showToast(message, 'warning');
    }
    
    showInfo(message) {
        this.showToast(message, 'info');
    }
    
    // File Upload Methods
    setupDragAndDrop() {
        const uploadArea = document.getElementById('uploadArea');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, this.preventDefaults);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                uploadArea.classList.add('drag-over');
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                uploadArea.classList.remove('drag-over');
            });
        });
        
        uploadArea.addEventListener('drop', (e) => {
            const files = Array.from(e.dataTransfer.files);
            this.handleFileSelection(files);
        });
        
        uploadArea.addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });
    }
    
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    handleFileSelection(files) {
        if (files.length === 0) return;
        
        this.uploadQueue = [];
        files.forEach(file => {
            this.uploadQueue.push({
                file,
                id: this.generateId(),
                status: 'pending'
            });
        });
        
        this.displaySelectedFiles();
    }
    
    displaySelectedFiles() {
        const fileList = document.getElementById('fileList');
        const selectedFiles = document.getElementById('selectedFiles');
        
        if (this.uploadQueue.length === 0) {
            fileList.classList.add('d-none');
            return;
        }
        
        fileList.classList.remove('d-none');
        
        selectedFiles.innerHTML = this.uploadQueue.map(item => `
            <div class="file-item" data-file-id="${item.id}">
                <div class="file-info">
                    <div class="file-name">
                        <i class="fas ${this.getFileIcon(item.file.type)} file-type-icon"></i>
                        ${item.file.name}
                    </div>
                    <div class="file-details">
                        Size: ${this.formatFileSize(item.file.size)} | 
                        Type: ${item.file.type || 'Unknown'} |
                        Modified: ${new Date(item.file.lastModified).toLocaleDateString()}
                    </div>
                </div>
                <button class="file-remove" onclick="app.removeFile('${item.id}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');
    }
    
    removeFile(fileId) {
        this.uploadQueue = this.uploadQueue.filter(item => item.id !== fileId);
        this.displaySelectedFiles();
    }
    
    clearFiles() {
        this.uploadQueue = [];
        this.displaySelectedFiles();
    }
    
    getFileIcon(mimeType) {
        if (!mimeType) return 'fa-file';
        
        if (mimeType.startsWith('image/')) return 'fa-file-image';
        if (mimeType.startsWith('video/')) return 'fa-file-video';
        if (mimeType.startsWith('audio/')) return 'fa-file-audio';
        if (mimeType.includes('pdf')) return 'fa-file-pdf';
        if (mimeType.includes('word')) return 'fa-file-word';
        if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return 'fa-file-excel';
        if (mimeType.includes('powerpoint') || mimeType.includes('presentation')) return 'fa-file-powerpoint';
        if (mimeType.includes('zip') || mimeType.includes('rar') || mimeType.includes('7z')) return 'fa-file-archive';
        if (mimeType.includes('text')) return 'fa-file-alt';
        
        return 'fa-file';
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    async uploadFiles() {
        if (this.uploadQueue.length === 0) {
            this.showWarning('No files selected for upload');
            return;
        }
        
        if (!this.authToken) {
            this.showError('Please login first');
            return;
        }
        
        const uploadBtn = document.getElementById('uploadBtn');
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Uploading...';
        
        for (const item of this.uploadQueue) {
            await this.uploadSingleFile(item);
        }
        
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '<i class="fas fa-upload me-2"></i>Upload Files';
        
        this.clearFiles();
        this.loadRecentTransfers();
    }
    
    async uploadSingleFile(fileItem) {
        const { file, id } = fileItem;
        
        try {
            // Create transfer item in UI
            this.addTransferToUI(fileItem, 'uploading');
            
            // Create FormData
            const formData = new FormData();
            formData.append('file', file);
            
            // Upload with progress tracking
            const response = await this.uploadWithProgress(formData, id);
            
            if (response.ok) {
                const result = await response.json();
                this.updateTransferStatus(id, 'completed');
                this.showSuccess(`${file.name} uploaded successfully! Compression ratio: ${result.compression_ratio}%`);
            } else {
                const error = await response.json();
                this.updateTransferStatus(id, 'failed');
                this.showError(`Upload failed for ${file.name}: ${error.error}`);
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.updateTransferStatus(id, 'failed');
            this.showError(`Upload failed for ${file.name}: ${error.message}`);
        }
    }
    
    async uploadWithProgress(formData, transferId) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    this.updateTransferProgress(transferId, percentComplete);
                }
            });
            
            xhr.addEventListener('load', () => {
                resolve(xhr);
            });
            
            xhr.addEventListener('error', () => {
                reject(new Error('Upload failed'));
            });
            
            xhr.open('POST', `${this.apiBaseUrl}/api/upload`);
            xhr.setRequestHeader('Authorization', `Bearer ${this.authToken}`);
            xhr.send(formData);
        });
    }
    
    addTransferToUI(fileItem, status) {
        const transferStatus = document.getElementById('transferStatus');
        const transferId = fileItem.id;
        
        // Remove empty state if present
        const emptyState = transferStatus.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
        
        const transferHtml = `
            <div class="transfer-item" data-transfer-id="${transferId}">
                <div class="transfer-icon">
                    <i class="fas fa-upload"></i>
                </div>
                <div class="transfer-details">
                    <div class="transfer-name">${fileItem.file.name}</div>
                    <div class="transfer-meta">
                        Size: ${this.formatFileSize(fileItem.file.size)}
                    </div>
                    <div class="progress-container mt-2">
                        <div class="progress">
                            <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                 role="progressbar" style="width: 0%">0%</div>
                        </div>
                    </div>
                </div>
                <div class="transfer-status">
                    <span class="status-badge status-${status}">${status}</span>
                </div>
            </div>
        `;
        
        transferStatus.insertAdjacentHTML('beforeend', transferHtml);
    }
    
    updateTransferProgress(transferId, progress) {
        const transferItem = document.querySelector(`[data-transfer-id="${transferId}"]`);
        if (transferItem) {
            const progressBar = transferItem.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.style.width = `${progress}%`;
                progressBar.textContent = `${Math.round(progress)}%`;
            }
        }
    }
    
    updateTransferStatus(transferId, status) {
        const transferItem = document.querySelector(`[data-transfer-id="${transferId}"]`);
        if (transferItem) {
            const statusBadge = transferItem.querySelector('.status-badge');
            if (statusBadge) {
                statusBadge.className = `status-badge status-${status}`;
                statusBadge.textContent = status;
            }
            
            if (status === 'completed' || status === 'failed') {
                const progressBar = transferItem.querySelector('.progress-bar');
                if (progressBar) {
                    progressBar.classList.remove('progress-bar-striped', 'progress-bar-animated');
                    if (status === 'completed') {
                        progressBar.style.width = '100%';
                        progressBar.textContent = '100%';
                    }
                }
            }
        }
    }
    
    // Transfer History Methods
    async loadRecentTransfers() {
        if (!this.authToken) return;
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/recent-transfers`, {
                headers: {
                    'Authorization': `Bearer ${this.authToken}`
                }
            });
            
            if (response.ok) {
                const transfers = await response.json();
                this.displayTransferHistory(transfers);
            } else {
                console.error('Failed to load recent transfers');
            }
        } catch (error) {
            console.error('Error loading recent transfers:', error);
        }
    }
    
    displayTransferHistory(transfers) {
        const tableBody = document.getElementById('transfersTableBody');
        
        if (transfers.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center">
                        <div class="empty-state-small">
                            <i class="fas fa-inbox"></i>
                            <p>No transfers yet</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        tableBody.innerHTML = transfers.map(transfer => `
            <tr>
                <td>
                    <i class="fas ${this.getFileIcon('')} me-2"></i>
                    ${transfer.filename}
                </td>
                <td>
                    <i class="fas fa-${transfer.type === 'upload' ? 'upload' : 'download'} me-1"></i>
                    ${transfer.type}
                </td>
                <td>${transfer.size}</td>
                <td>${transfer.compressed_size || 'N/A'}</td>
                <td>
                    ${transfer.compression_ratio ? 
                        `<span class="compression-badge">${transfer.compression_ratio}%</span>` : 
                        'N/A'
                    }
                </td>
                <td>${new Date(transfer.timestamp).toLocaleString()}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="app.downloadFile('${transfer.id}')" 
                            ${transfer.type !== 'upload' ? 'disabled' : ''}>
                        <i class="fas fa-download"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    }
    
    async downloadFile(transferId) {
        if (!this.authToken) {
            this.showError('Please login first');
            return;
        }
        
        try {
            this.showInfo('Starting download...');
            
            const response = await fetch(`${this.apiBaseUrl}/api/download/${transferId}`, {
                headers: {
                    'Authorization': `Bearer ${this.authToken}`
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                
                // Create download link
                const blob = new Blob([this.base64ToArrayBuffer(result.data)], 
                    { type: 'application/octet-stream' });
                const url = window.URL.createObjectURL(blob);
                
                const a = document.createElement('a');
                a.href = url;
                a.download = result.filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.showSuccess(`${result.filename} downloaded successfully!`);
            } else {
                const error = await response.json();
                this.showError(`Download failed: ${error.error}`);
            }
        } catch (error) {
            console.error('Download error:', error);
            this.showError('Download failed');
        }
    }
    
    base64ToArrayBuffer(base64) {
        const binaryString = window.atob(base64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes.buffer;
    }
    
    // Utility Methods
    generateId() {
        return 'transfer-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }
    
    // Event Listeners Setup
    setupEventListeners() {
        // Navigation
        document.getElementById('loginNavBtn').addEventListener('click', () => {
            this.showModal('loginModal');
        });
        
        document.getElementById('logoutNavBtn').addEventListener('click', () => {
            this.logout();
        });
        
        // Welcome section buttons
        document.getElementById('showLoginBtn').addEventListener('click', () => {
            this.showModal('loginModal');
        });
        
        document.getElementById('showRegisterBtn').addEventListener('click', () => {
            this.showModal('registerModal');
        });
        
        // Login form
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('loginUsername').value.trim();
            const password = document.getElementById('loginPassword').value;
            
            if (!username || !password) {
                this.showError('Please enter both username and password');
                return;
            }
            
            await this.login(username, password);
        });
        
        // Register form
        document.getElementById('registerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('regUsername').value.trim();
            const email = document.getElementById('regEmail').value.trim();
            const password = document.getElementById('regPassword').value;
            const confirmPassword = document.getElementById('regPasswordConfirm').value;
            
            if (!username || !password) {
                this.showError('Username and password are required');
                return;
            }
            
            if (password.length < 8) {
                this.showError('Password must be at least 8 characters long');
                return;
            }
            
            if (password !== confirmPassword) {
                this.showError('Passwords do not match');
                return;
            }
            
            await this.register(username, email, password);
        });
        
        // Password toggle
        document.getElementById('togglePassword').addEventListener('click', () => {
            const passwordInput = document.getElementById('loginPassword');
            const toggleIcon = document.querySelector('#togglePassword i');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                toggleIcon.className = 'fas fa-eye-slash';
            } else {
                passwordInput.type = 'password';
                toggleIcon.className = 'fas fa-eye';
            }
        });
        
        // File input
        document.getElementById('fileInput').addEventListener('change', (e) => {
            this.handleFileSelection(Array.from(e.target.files));
        });
        
        document.getElementById('selectFilesBtn').addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });
        
        // Upload controls
        document.getElementById('uploadBtn').addEventListener('click', () => {
            this.uploadFiles();
        });
        
        document.getElementById('clearFilesBtn').addEventListener('click', () => {
            this.clearFiles();
        });
        
        // Refresh buttons
        document.getElementById('refreshTransfersBtn').addEventListener('click', () => {
            this.loadRecentTransfers();
        });
        
        document.getElementById('refreshHistoryBtn').addEventListener('click', () => {
            this.loadRecentTransfers();
        });
        
        // Clear forms when modals are hidden
        document.getElementById('loginModal').addEventListener('hidden.bs.modal', () => {
            document.getElementById('loginForm').reset();
        });
        
        document.getElementById('registerModal').addEventListener('hidden.bs.modal', () => {
            document.getElementById('registerForm').reset();
        });
    }
}

// Initialize the application
const app = new SFTPApp();

// Global functions for onclick handlers
window.app = app;

// Service worker removed for simplified deployment
