/**
 * Sistema de Notificaciones en Tiempo Real
 * Maneja notificaciones push con Socket.IO
 */

class NotificationSystem {
    constructor() {
        this.notifications = [];
        this.unreadCount = 0;
        this.socket = null;
        this.soundEnabled = localStorage.getItem('notifications_sound') !== 'false';
        this.isOpen = false;

        this.init();
    }

    init() {
        // Conectar Socket.IO si está disponible
        if (typeof io !== 'undefined') {
            this.connectSocket();
        }

        // Cargar notificaciones iniciales
        this.loadNotifications();

        // Crear elementos del DOM
        this.createNotificationElements();

        // Configurar event listeners
        this.setupEventListeners();

        // Actualizar badge
        this.updateBadge();
    }

    connectSocket() {
        try {
            this.socket = io();

            // Unirse a la sala de admins
            this.socket.emit('join_room', 'admins');

            // Escuchar nuevas notificaciones
            this.socket.on('new_notification', (notification) => {
                this.handleNewNotification(notification);
            });

            console.log('✅ Sistema de notificaciones conectado');
        } catch (error) {
            console.error('Error al conectar Socket.IO:', error);
        }
    }

    createNotificationElements() {
        // Verificar si ya existen
        if (document.getElementById('notification-bell')) {
            return;
        }

        // Crear campana de notificaciones en el header
        const header = document.querySelector('.admin-header') || document.querySelector('header');
        if (!header) return;

        const bellContainer = document.createElement('div');
        bellContainer.className = 'notification-bell-container';
        bellContainer.innerHTML = `
            <button id="notification-bell" class="notification-bell" aria-label="Notificaciones">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                    <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                </svg>
                <span id="notification-badge" class="notification-badge" style="display: none;">0</span>
            </button>
        `;

        // Insertar antes del último elemento del header
        header.appendChild(bellContainer);

        // Crear panel de notificaciones
        const panel = document.createElement('div');
        panel.id = 'notification-panel';
        panel.className = 'notification-panel';
        panel.style.display = 'none';
        panel.innerHTML = `
            <div class="notification-panel-header">
                <h3>Notificaciones</h3>
                <div class="notification-panel-actions">
                    <button id="mark-all-read" class="btn-text" title="Marcar todas como leídas">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                    </button>
                    <button id="notification-settings" class="btn-text" title="Configuración">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="3"></circle>
                            <path d="M12 1v6m0 6v6m9-9h-6m-6 0H3"></path>
                        </svg>
                    </button>
                    <button id="close-notifications" class="btn-text" title="Cerrar">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
            </div>
            <div id="notification-list" class="notification-list">
                <div class="notification-empty">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                        <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                    </svg>
                    <p>No hay notificaciones</p>
                </div>
            </div>
        `;

        document.body.appendChild(panel);
    }

    setupEventListeners() {
        // Toggle panel
        const bell = document.getElementById('notification-bell');
        if (bell) {
            bell.addEventListener('click', () => this.togglePanel());
        }

        // Cerrar panel
        const closeBtn = document.getElementById('close-notifications');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closePanel());
        }

        // Marcar todas como leídas
        const markAllBtn = document.getElementById('mark-all-read');
        if (markAllBtn) {
            markAllBtn.addEventListener('click', () => this.markAllAsRead());
        }

        // Configuración
        const settingsBtn = document.getElementById('notification-settings');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.showSettings());
        }

        // Cerrar al hacer click fuera
        document.addEventListener('click', (e) => {
            const panel = document.getElementById('notification-panel');
            const bell = document.getElementById('notification-bell');

            if (this.isOpen && panel && bell &&
                !panel.contains(e.target) && !bell.contains(e.target)) {
                this.closePanel();
            }
        });
    }

    async loadNotifications() {
        try {
            const response = await fetch('/admin/api/notifications');
            const data = await response.json();

            if (data.success) {
                this.notifications = data.notifications || [];
                this.unreadCount = data.unread_count || 0;
                this.updateBadge();
                this.renderNotifications();
            }
        } catch (error) {
            console.error('Error al cargar notificaciones:', error);
        }
    }

    handleNewNotification(notification) {
        // Agregar a la lista
        this.notifications.unshift(notification);
        this.unreadCount++;

        // Actualizar UI
        this.updateBadge();
        this.renderNotifications();

        // Mostrar toast
        this.showToast(notification);

        // Reproducir sonido
        if (this.soundEnabled) {
            this.playNotificationSound(notification.priority);
        }

        // Animación de la campana
        this.animateBell();
    }

    togglePanel() {
        const panel = document.getElementById('notification-panel');
        if (!panel) return;

        if (this.isOpen) {
            this.closePanel();
        } else {
            this.openPanel();
        }
    }

    openPanel() {
        const panel = document.getElementById('notification-panel');
        if (!panel) return;

        panel.style.display = 'block';
        setTimeout(() => panel.classList.add('show'), 10);
        this.isOpen = true;

        // Cargar notificaciones actualizadas
        this.loadNotifications();
    }

    closePanel() {
        const panel = document.getElementById('notification-panel');
        if (!panel) return;

        panel.classList.remove('show');
        setTimeout(() => {
            panel.style.display = 'none';
            this.isOpen = false;
        }, 300);
    }

    renderNotifications() {
        const list = document.getElementById('notification-list');
        if (!list) return;

        if (this.notifications.length === 0) {
            list.innerHTML = `
                <div class="notification-empty">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                        <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                    </svg>
                    <p>No hay notificaciones</p>
                </div>
            `;
            return;
        }

        list.innerHTML = this.notifications.map(n => this.renderNotification(n)).join('');

        // Agregar event listeners
        list.querySelectorAll('.notification-item').forEach(item => {
            const id = item.dataset.id;

            item.addEventListener('click', () => {
                this.markAsRead(id);
                const notification = this.notifications.find(n => n.id == id);
                if (notification && notification.action_url) {
                    window.location.href = notification.action_url;
                }
            });

            const dismissBtn = item.querySelector('.notification-dismiss');
            if (dismissBtn) {
                dismissBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.dismiss(id);
                });
            }
        });
    }

    renderNotification(notification) {
        const icon = this.getNotificationIcon(notification.type);
        const timeAgo = this.getTimeAgo(notification.created_at_timestamp);
        const priorityClass = `priority-${notification.priority}`;
        const readClass = notification.is_read ? 'read' : 'unread';

        return `
            <div class="notification-item ${readClass} ${priorityClass}" data-id="${notification.id}">
                <div class="notification-icon ${notification.type}">
                    ${icon}
                </div>
                <div class="notification-content">
                    <div class="notification-title">${notification.title}</div>
                    <div class="notification-message">${notification.message}</div>
                    <div class="notification-time">${timeAgo}</div>
                </div>
                <button class="notification-dismiss" title="Descartar">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
        `;
    }

    getNotificationIcon(type) {
        const icons = {
            'cierre_pendiente': '💰',
            'diferencia_grande': '⚠️',
            'fraude': '🚨',
            'turno_abierto': '✅',
            'turno_cerrado': '🏁',
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌'
        };

        return icons[type] || 'ℹ️';
    }

    getTimeAgo(timestamp) {
        if (!timestamp) return 'Ahora';

        const now = Date.now() / 1000;
        const diff = now - timestamp;

        if (diff < 60) return 'Ahora';
        if (diff < 3600) return `Hace ${Math.floor(diff / 60)} min`;
        if (diff < 86400) return `Hace ${Math.floor(diff / 3600)} h`;
        return `Hace ${Math.floor(diff / 86400)} días`;
    }

    updateBadge() {
        const badge = document.getElementById('notification-badge');
        if (!badge) return;

        if (this.unreadCount > 0) {
            badge.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    }

    showToast(notification) {
        const toast = document.createElement('div');
        toast.className = `notification-toast ${notification.type} priority-${notification.priority}`;
        toast.innerHTML = `
            <div class="toast-icon">${this.getNotificationIcon(notification.type)}</div>
            <div class="toast-content">
                <div class="toast-title">${notification.title}</div>
                <div class="toast-message">${notification.message}</div>
            </div>
            <button class="toast-close">×</button>
        `;

        document.body.appendChild(toast);

        // Animar entrada
        setTimeout(() => toast.classList.add('show'), 10);

        // Auto-cerrar después de 5 segundos
        const autoClose = setTimeout(() => this.closeToast(toast), 5000);

        // Botón de cerrar
        toast.querySelector('.toast-close').addEventListener('click', () => {
            clearTimeout(autoClose);
            this.closeToast(toast);
        });

        // Click en el toast para ir a la acción
        toast.addEventListener('click', (e) => {
            if (!e.target.classList.contains('toast-close')) {
                if (notification.action_url) {
                    window.location.href = notification.action_url;
                }
                clearTimeout(autoClose);
                this.closeToast(toast);
            }
        });
    }

    closeToast(toast) {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }

    animateBell() {
        const bell = document.getElementById('notification-bell');
        if (!bell) return;

        bell.classList.add('ring');
        setTimeout(() => bell.classList.remove('ring'), 1000);
    }

    playNotificationSound(priority) {
        // Diferentes tonos según prioridad
        const frequencies = {
            1: 400,  // Baja
            2: 600,  // Normal
            3: 800,  // Alta
            4: 1000  // Crítica
        };

        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.frequency.value = frequencies[priority] || 600;
            oscillator.type = 'sine';

            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.3);
        } catch (error) {
            console.error('Error al reproducir sonido:', error);
        }
    }

    async markAsRead(notificationId) {
        try {
            const response = await fetch(`/admin/api/notifications/${notificationId}/read`, {
                method: 'POST'
            });

            if (response.ok) {
                const notification = this.notifications.find(n => n.id == notificationId);
                if (notification && !notification.is_read) {
                    notification.is_read = true;
                    this.unreadCount = Math.max(0, this.unreadCount - 1);
                    this.updateBadge();
                    this.renderNotifications();
                }
            }
        } catch (error) {
            console.error('Error al marcar como leída:', error);
        }
    }

    async markAllAsRead() {
        try {
            const response = await fetch('/admin/api/notifications/read-all', {
                method: 'POST'
            });

            if (response.ok) {
                this.notifications.forEach(n => n.is_read = true);
                this.unreadCount = 0;
                this.updateBadge();
                this.renderNotifications();
            }
        } catch (error) {
            console.error('Error al marcar todas como leídas:', error);
        }
    }

    async dismiss(notificationId) {
        try {
            const response = await fetch(`/admin/api/notifications/${notificationId}/dismiss`, {
                method: 'POST'
            });

            if (response.ok) {
                const index = this.notifications.findIndex(n => n.id == notificationId);
                if (index !== -1) {
                    const notification = this.notifications[index];
                    if (!notification.is_read) {
                        this.unreadCount = Math.max(0, this.unreadCount - 1);
                    }
                    this.notifications.splice(index, 1);
                    this.updateBadge();
                    this.renderNotifications();
                }
            }
        } catch (error) {
            console.error('Error al descartar notificación:', error);
        }
    }

    showSettings() {
        const soundEnabled = this.soundEnabled;

        const modal = createModal('Configuración de Notificaciones', `
            <div class="notification-settings">
                <label class="setting-item">
                    <input type="checkbox" id="sound-toggle" ${soundEnabled ? 'checked' : ''}>
                    <span>Sonidos de notificación</span>
                </label>
            </div>
            <div style="margin-top: 20px;">
                <button class="btn btn-primary" onclick="notificationSystem.saveSettings()">Guardar</button>
            </div>
        `);
    }

    saveSettings() {
        const soundToggle = document.getElementById('sound-toggle');
        if (soundToggle) {
            this.soundEnabled = soundToggle.checked;
            localStorage.setItem('notifications_sound', this.soundEnabled);
        }

        // Cerrar modal
        const modal = document.querySelector('.modal');
        if (modal) {
            closeModal(modal.id);
        }
    }
}

// Inicializar sistema de notificaciones cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.notificationSystem = new NotificationSystem();
    });
} else {
    window.notificationSystem = new NotificationSystem();
}
