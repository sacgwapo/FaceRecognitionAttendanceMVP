const API_BASE = '';

function getAuthToken() {
    return localStorage.getItem('access_token');
}

async function fetchAPI(url, options = {}) {
    const token = getAuthToken();

    const defaultHeaders = {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };

    if (options.body && typeof options.body === 'string') {
        defaultHeaders['Content-Type'] = 'application/json';
    }

    const mergedOptions = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...(options.headers || {})
        }
    };

    try {
        const response = await fetch(API_BASE + url, mergedOptions);

        if (response.status === 401) {
            localStorage.removeItem('access_token');
            window.location.href = '/login';
            throw new Error('Unauthorized');
        }

        if (response.status === 204 || response.headers.get('content-length') === '0') {
            return {};
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Request failed');
            }

            return data;
        } else {
            if (!response.ok) {
                throw new Error('Request failed');
            }
            return {};
        }
    } catch (error) {
        if (error instanceof SyntaxError) {
            console.error('JSON Parse Error:', error);
            throw new Error('Invalid server response');
        }
        console.error('API Error:', error);
        throw error;
    }
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function formatTime(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatDateTime(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });
}

function updateCurrentTime() {
    const timeEl = document.getElementById('current-time');
    if (timeEl) {
        const now = new Date();
        timeEl.textContent = now.toLocaleString('en-US', {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        });
    }
}

function setActiveNavLink() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

function checkAuth() {
    const publicPages = ['/', '/login'];
    const currentPath = window.location.pathname;

    if (!publicPages.includes(currentPath) && !getAuthToken()) {
        window.location.href = '/login';
        return false;
    }

    return true;
}

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setActiveNavLink();
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);

    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            try {
                await fetchAPI('/api/auth/logout', { method: 'POST' });
            } catch (e) {
            }
            localStorage.removeItem('access_token');
            window.location.href = '/login';
        });
    }

    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('sidebar');
    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });

        document.addEventListener('click', (e) => {
            if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        });
    }
});
