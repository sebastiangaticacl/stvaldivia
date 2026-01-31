/**
 * Sistema de Confirmaciones Personalizadas
 * Reemplaza los confirm() básicos con modales elegantes
 */

// Crear estilos CSS para el modal de confirmación
function injectConfirmStyles() {
    if (document.getElementById('confirm-modal-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'confirm-modal-styles';
    style.textContent = `
        .confirm-modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 99999;
            animation: fadeIn 0.3s ease-out;
        }

        .confirm-modal {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 2px solid rgba(102, 126, 234, 0.5);
            border-radius: 15px;
            padding: 30px;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
            animation: slideInScale 0.3s ease-out;
            z-index: 100000;
        }

        .confirm-modal-title {
            color: #fff;
            font-size: 1.5rem;
            font-weight: bold;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .confirm-modal-message {
            color: #ccc;
            font-size: 1.1rem;
            margin-bottom: 25px;
            line-height: 1.5;
        }

        .confirm-modal-buttons {
            display: flex;
            gap: 15px;
            justify-content: flex-end;
        }

        .confirm-btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            min-width: 100px;
        }

        .confirm-btn-primary {
            background: #667eea;
            color: white;
        }

        .confirm-btn-primary:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 4px 10px rgba(102, 126, 234, 0.4);
        }

        .confirm-btn-secondary {
            background: #2a2a3e;
            color: #ccc;
            border: 2px solid rgba(102, 126, 234, 0.3);
        }

        .confirm-btn-secondary:hover {
            background: #3a3a4e;
            border-color: rgba(102, 126, 234, 0.5);
        }

        .confirm-btn-danger {
            background: #ff4444;
            color: white;
        }

        .confirm-btn-danger:hover {
            background: #dd3333;
            transform: translateY(-2px);
            box-shadow: 0 4px 10px rgba(255, 68, 68, 0.4);
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes slideInScale {
            from {
                opacity: 0;
                transform: scale(0.9) translateY(-20px);
            }
            to {
                opacity: 1;
                transform: scale(1) translateY(0);
            }
        }

        @media (max-width: 480px) {
            .confirm-modal {
                padding: 20px;
                width: 95%;
            }

            .confirm-modal-buttons {
                flex-direction: column;
            }

            .confirm-btn {
                width: 100%;
            }
        }
    `;
    document.head.appendChild(style);
}

/**
 * Muestra un modal de confirmación personalizado
 * @param {string} message - Mensaje a mostrar
 * @param {string} title - Título del modal (opcional)
 * @param {object} options - Opciones adicionales
 * @returns {Promise<boolean>} - true si confirma, false si cancela
 */
function confirmDialog(message, title = 'Confirmar', options = {}) {
    return new Promise((resolve) => {
        // Inyectar estilos si no existen
        injectConfirmStyles();
        
        // Crear overlay
        const overlay = document.createElement('div');
        overlay.className = 'confirm-modal-overlay';
        
        // Crear modal
        const modal = document.createElement('div');
        modal.className = 'confirm-modal';
        
        // Título
        const titleDiv = document.createElement('div');
        titleDiv.className = 'confirm-modal-title';
        titleDiv.innerHTML = `
            <span>${options.icon || '⚠️'}</span>
            <span>${title}</span>
        `;
        
        // Mensaje
        const messageDiv = document.createElement('div');
        messageDiv.className = 'confirm-modal-message';
        messageDiv.textContent = message;
        
        // Botones
        const buttonsDiv = document.createElement('div');
        buttonsDiv.className = 'confirm-modal-buttons';
        
        const confirmText = options.confirmText || 'Confirmar';
        const cancelText = options.cancelText || 'Cancelar';
        const type = options.type || 'primary'; // primary, danger
        
        const confirmBtn = document.createElement('button');
        confirmBtn.className = `confirm-btn confirm-btn-${type}`;
        confirmBtn.textContent = confirmText;
        confirmBtn.onclick = () => {
            overlay.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {
                overlay.remove();
                resolve(true);
            }, 300);
        };
        
        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'confirm-btn confirm-btn-secondary';
        cancelBtn.textContent = cancelText;
        cancelBtn.onclick = () => {
            overlay.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {
                overlay.remove();
                resolve(false);
            }, 300);
        };
        
        buttonsDiv.appendChild(cancelBtn);
        buttonsDiv.appendChild(confirmBtn);
        
        modal.appendChild(titleDiv);
        modal.appendChild(messageDiv);
        modal.appendChild(buttonsDiv);
        
        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        
        // Cerrar al hacer click fuera del modal
        overlay.onclick = (e) => {
            if (e.target === overlay) {
                cancelBtn.click();
            }
        };
        
        // Cerrar con ESC
        const handleEsc = (e) => {
            if (e.key === 'Escape') {
                cancelBtn.click();
                document.removeEventListener('keydown', handleEsc);
            }
        };
        document.addEventListener('keydown', handleEsc);
        
        // Focus en el botón de confirmar
        setTimeout(() => {
            if (options.autoFocus !== false) {
                confirmBtn.focus();
            }
        }, 100);
    });
}

/**
 * Confirmación de acción destructiva (rojo)
 */
function confirmDanger(message, title = '⚠️ Confirmar Acción') {
    return confirmDialog(message, title, {
        type: 'danger',
        icon: '⚠️',
        confirmText: 'Sí, continuar',
        cancelText: 'Cancelar'
    });
}

/**
 * Confirmación simple (azul)
 */
function confirmAction(message, title = '✓ Confirmar') {
    return confirmDialog(message, title, {
        type: 'primary',
        icon: '✓',
        confirmText: 'Confirmar',
        cancelText: 'Cancelar'
    });
}

// Agregar animación de fadeOut si no existe
if (!document.getElementById('confirm-modal-styles')) {
    const style = document.createElement('style');
    style.textContent += `
        @keyframes fadeOut {
            from { opacity: 1; }
            to { opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}

// Inyectar estilos al cargar
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectConfirmStyles);
} else {
    injectConfirmStyles();
}








