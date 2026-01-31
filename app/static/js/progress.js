/**
 * Sistema de Progress Bars y Toast Notifications mejorado
 */

// Progress Bar Component
class ProgressBar {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId) || document.body;
        this.options = {
            showPercentage: options.showPercentage !== false,
            autoHide: options.autoHide !== false,
            hideDelay: options.hideDelay || 2000,
            ...options
        };
        this.bar = null;
    }

    show(percentage = 0, message = '') {
        if (!this.bar) {
            this.bar = document.createElement('div');
            this.bar.className = 'progress-bar-container';
            this.bar.innerHTML = `
                <div class="progress-bar-wrapper">
                    <div class="progress-bar-fill" style="width: ${percentage}%"></div>
                    ${this.options.showPercentage ? `<span class="progress-bar-text">${percentage}%</span>` : ''}
                </div>
                ${message ? `<div class="progress-bar-message">${message}</div>` : ''}
            `;
            this.container.appendChild(this.bar);
        }
        this.update(percentage, message);
    }

    update(percentage, message = '') {
        if (!this.bar) return;
        
        const fill = this.bar.querySelector('.progress-bar-fill');
        const text = this.bar.querySelector('.progress-bar-text');
        const msg = this.bar.querySelector('.progress-bar-message');
        
        if (fill) fill.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
        if (text) text.textContent = `${Math.round(percentage)}%`;
        if (msg && message) msg.textContent = message;
    }

    hide() {
        if (this.bar) {
            this.bar.classList.add('progress-bar-hiding');
            setTimeout(() => {
                if (this.bar && this.bar.parentNode) {
                    this.bar.parentNode.removeChild(this.bar);
                }
                this.bar = null;
            }, 300);
        }
    }

    complete(message = 'Completado') {
        this.update(100, message);
        if (this.options.autoHide) {
            setTimeout(() => this.hide(), this.options.hideDelay);
        }
    }
}

// Toast Notification System
class ToastManager {
    constructor() {
        this.container = null;
        this.toasts = [];
        this.init();
    }

    init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    }

    show(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const icon = this.getIcon(type);
        toast.innerHTML = `
            <div class="toast-icon">${icon}</div>
            <div class="toast-message">${message}</div>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        this.container.appendChild(toast);
        
        // Animar entrada
        setTimeout(() => toast.classList.add('toast-show'), 10);
        
        // Auto-remover
        if (duration > 0) {
            setTimeout(() => {
                toast.classList.remove('toast-show');
                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast);
                    }
                }, 300);
            }, duration);
        }
        
        return toast;
    }

    getIcon(type) {
        const icons = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        };
        return icons[type] || icons.info;
    }

    success(message, duration = 5000) {
        return this.show(message, 'success', duration);
    }

    error(message, duration = 7000) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration = 6000) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration = 5000) {
        return this.show(message, 'info', duration);
    }
}

// Instancia global
window.toastManager = new ToastManager();
window.ProgressBar = ProgressBar;

// Helper functions para compatibilidad
function showProgress(containerId, percentage, message) {
    if (!window.progressBars) window.progressBars = {};
    if (!window.progressBars[containerId]) {
        window.progressBars[containerId] = new ProgressBar(containerId);
    }
    window.progressBars[containerId].show(percentage, message);
}

function hideProgress(containerId) {
    if (window.progressBars && window.progressBars[containerId]) {
        window.progressBars[containerId].hide();
    }
}

function showToast(message, type = 'info') {
    return window.toastManager.show(message, type);
}





