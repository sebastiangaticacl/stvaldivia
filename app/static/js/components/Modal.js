/**
 * Componente de Modal reutilizable
 * Proporciona funciones comunes para crear y manejar modales
 */

/**
 * Crea y muestra un modal simple
 * @param {string} title - Título del modal
 * @param {string} content - Contenido HTML del modal
 * @param {Object} options - Opciones adicionales
 * @returns {HTMLElement} Elemento del modal creado
 */
function createModal(title, content, options = {}) {
    const {
        id = `modal-${Date.now()}`,
        closeOnClickOutside = true,
        closeOnEscape = true,
        showCloseButton = true,
        className = ''
    } = options;
    
    // Remover modal existente con el mismo ID si existe
    const existingModal = document.getElementById(id);
    if (existingModal) {
        existingModal.remove();
    }
    
    // Crear estructura del modal
    const modal = document.createElement('div');
    modal.id = id;
    modal.className = `modal-overlay ${className}`;
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;
    
    const modalContent = document.createElement('div');
    modalContent.className = 'modal-content';
    modalContent.style.cssText = `
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 2px solid rgba(102, 126, 234, 0.3);
        border-radius: 15px;
        padding: 30px;
        max-width: 90%;
        max-height: 90%;
        overflow-y: auto;
        position: relative;
        transform: scale(0.9);
        transition: transform 0.3s ease;
    `;
    
    // Header del modal
    const modalHeader = document.createElement('div');
    modalHeader.style.cssText = `
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        padding-bottom: 15px;
        border-bottom: 1px solid rgba(102, 126, 234, 0.3);
    `;
    
    const modalTitle = document.createElement('h2');
    modalTitle.textContent = title;
    modalTitle.style.cssText = `
        margin: 0;
        color: #fff;
        font-size: 1.5rem;
    `;
    
    modalHeader.appendChild(modalTitle);
    
    // Botón de cerrar
    if (showCloseButton) {
        const closeButton = document.createElement('button');
        closeButton.innerHTML = '&times;';
        closeButton.className = 'modal-close-btn';
        closeButton.style.cssText = `
            background: transparent;
            border: none;
            color: #fff;
            font-size: 2rem;
            cursor: pointer;
            padding: 0;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: color 0.3s ease;
        `;
        
        closeButton.addEventListener('mouseenter', () => {
            closeButton.style.color = '#667eea';
        });
        closeButton.addEventListener('mouseleave', () => {
            closeButton.style.color = '#fff';
        });
        
        closeButton.addEventListener('click', () => closeModal(id));
        modalHeader.appendChild(closeButton);
    }
    
    // Contenido del modal
    const modalBody = document.createElement('div');
    modalBody.innerHTML = content;
    modalBody.style.cssText = `
        color: #e8e8e8;
    `;
    
    // Ensamblar modal
    modalContent.appendChild(modalHeader);
    modalContent.appendChild(modalBody);
    modal.appendChild(modalContent);
    
    // Agregar al DOM
    document.body.appendChild(modal);
    
    // Animar entrada
    setTimeout(() => {
        modal.style.opacity = '1';
        modalContent.style.transform = 'scale(1)';
    }, 10);
    
    // Cerrar al hacer clic fuera
    if (closeOnClickOutside) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal(id);
            }
        });
    }
    
    // Cerrar con Escape
    if (closeOnEscape) {
        const escapeHandler = (e) => {
            if (e.key === 'Escape' && document.getElementById(id)) {
                closeModal(id);
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);
    }
    
    return modal;
}

/**
 * Cierra un modal por ID
 * @param {string} modalId - ID del modal a cerrar
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    
    const modalContent = modal.querySelector('.modal-content');
    if (modalContent) {
        modalContent.style.transform = 'scale(0.9)';
    }
    
    modal.style.opacity = '0';
    
    setTimeout(() => {
        modal.remove();
    }, 300);
}

/**
 * Muestra un modal de confirmación
 * @param {string} message - Mensaje de confirmación
 * @param {Function} onConfirm - Callback cuando se confirma
 * @param {Function} onCancel - Callback cuando se cancela (opcional)
 */
function showConfirmModal(message, onConfirm, onCancel = null) {
    const content = `
        <div style="text-align: center; padding: 20px;">
            <p style="font-size: 1.1rem; margin-bottom: 30px;">${message}</p>
            <div style="display: flex; gap: 15px; justify-content: center;">
                <button class="btn-confirm" style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border: none;
                    color: white;
                    padding: 12px 30px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 1rem;
                    transition: transform 0.2s ease;
                ">Confirmar</button>
                <button class="btn-cancel" style="
                    background: #444;
                    border: none;
                    color: white;
                    padding: 12px 30px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 1rem;
                    transition: transform 0.2s ease;
                ">Cancelar</button>
            </div>
        </div>
    `;
    
    const modal = createModal('Confirmar', content, {
        id: 'confirm-modal',
        closeOnClickOutside: false
    });
    
    const confirmBtn = modal.querySelector('.btn-confirm');
    const cancelBtn = modal.querySelector('.btn-cancel');
    
    confirmBtn.addEventListener('click', () => {
        closeModal('confirm-modal');
        if (onConfirm) onConfirm();
    });
    
    cancelBtn.addEventListener('click', () => {
        closeModal('confirm-modal');
        if (onCancel) onCancel();
    });
    
    confirmBtn.addEventListener('mouseenter', () => {
        confirmBtn.style.transform = 'scale(1.05)';
    });
    confirmBtn.addEventListener('mouseleave', () => {
        confirmBtn.style.transform = 'scale(1)';
    });
    
    cancelBtn.addEventListener('mouseenter', () => {
        cancelBtn.style.transform = 'scale(1.05)';
    });
    cancelBtn.addEventListener('mouseleave', () => {
        cancelBtn.style.transform = 'scale(1)';
    });
}

// Exportar funciones para uso global
window.createModal = createModal;
window.closeModal = closeModal;
window.showConfirmModal = showConfirmModal;

