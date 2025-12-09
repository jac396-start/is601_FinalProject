// Your JavaScript code can go here.
// static/js/script.js
/**
 * Main JavaScript file for the Calculator Application
 * Handles client-side functionality for authentication and calculations
 */

// Global configuration
const API_BASE_URL = window.location.origin;

/**
 * Utility Functions
 */

// Get token from localStorage
function getToken() {
    return localStorage.getItem('access_token');
}

// Check if user is authenticated
function isAuthenticated() {
    return !!getToken();
}

// Redirect to login if not authenticated
function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

// Make authenticated API request
async function authenticatedFetch(url, options = {}) {
    const token = getToken();
    
    if (!token) {
        throw new Error('No authentication token found');
    }
    
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    const response = await fetch(url, {
        ...options,
        headers
    });
    
    // Handle 401 Unauthorized
    if (response.status === 401) {
        localStorage.clear();
        window.location.href = '/login';
        throw new Error('Session expired. Please login again.');
    }
    
    return response;
}

/**
 * Alert/Notification Functions
 */

function showAlert(type, message) {
    const alertId = type === 'error' ? 'errorAlert' : 'successAlert';
    const messageId = type === 'error' ? 'errorMessage' : 'successMessage';
    
    const alertElement = document.getElementById(alertId);
    const messageElement = document.getElementById(messageId);
    
    if (!alertElement || !messageElement) return;
    
    messageElement.textContent = message;
    alertElement.classList.remove('hidden');
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        alertElement.classList.add('opacity-0');
        setTimeout(() => {
            alertElement.classList.add('hidden');
            alertElement.classList.remove('opacity-0');
        }, 300);
    }, 5000);
    
    // Scroll to alert
    alertElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function showError(message) {
    showAlert('error', message);
}

function showSuccess(message) {
    showAlert('success', message);
}

/**
 * Form Validation Functions
 */

function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function validatePassword(password) {
    // At least 8 characters, one uppercase, one lowercase, one number
    return password.length >= 8 &&
           /[A-Z]/.test(password) &&
           /[a-z]/.test(password) &&
           /[0-9]/.test(password);
}

function validateUsername(username) {
    // 3-20 characters, alphanumeric and underscore only
    return /^[a-zA-Z0-9_]{3,20}$/.test(username);
}

/**
 * Number Input Validation
 */

function parseNumberInputs(inputString) {
    const numbers = inputString
        .split(',')
        .map(s => s.trim())
        .filter(s => s !== '')
        .map(s => parseFloat(s))
        .filter(n => !isNaN(n));
    
    return numbers;
}

function validateCalculationInputs(inputs, operationType) {
    if (!Array.isArray(inputs) || inputs.length < 2) {
        throw new Error('Please enter at least two valid numbers');
    }
    
    // Check for division by zero
    if (operationType === 'division') {
        const divisors = inputs.slice(1);
        if (divisors.some(n => n === 0)) {
            throw new Error('Cannot divide by zero');
        }
    }
    
    return true;
}

/**
 * Formatting Functions
 */

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatDateTime(dateString) {
    return `${formatDate(dateString)} ${formatTime(dateString)}`;
}

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Export functions for use in other scripts
 */
window.calculatorApp = {
    // Authentication
    getToken,
    isAuthenticated,
    requireAuth,
    authenticatedFetch,
    
    // Alerts
    showError,
    showSuccess,
    showAlert,
    
    // Validation
    validateEmail,
    validatePassword,
    validateUsername,
    parseNumberInputs,
    validateCalculationInputs,
    
    // Formatting
    formatDate,
    formatTime,
    formatDateTime,
    capitalizeFirst,
    
    // Configuration
    API_BASE_URL
};

console.log("Calculator App JavaScript loaded successfully!");
