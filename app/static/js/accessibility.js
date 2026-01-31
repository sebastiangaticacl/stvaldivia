/**
 * Mejoras de Accesibilidad
 * Funciones para mejorar la accesibilidad de la aplicación
 */

// Mejoras de navegación por teclado
function initKeyboardNavigation() {
    // Agregar soporte para navegación con Tab en elementos personalizados
    document.addEventListener('keydown', function(e) {
        // Permitir activar botones y enlaces con Enter/Space
        if ((e.key === 'Enter' || e.key === ' ') && e.target.hasAttribute('role') && e.target.getAttribute('role') === 'button') {
            e.preventDefault();
            e.target.click();
        }
        
        // Navegación con flechas en listas
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
            const focused = document.activeElement;
            if (focused && focused.hasAttribute('data-keyboard-navigable')) {
                e.preventDefault();
                const items = Array.from(document.querySelectorAll('[data-keyboard-navigable]'));
                const currentIndex = items.indexOf(focused);
                
                if (currentIndex !== -1) {
                    const nextIndex = e.key === 'ArrowDown' 
                        ? (currentIndex + 1) % items.length
                        : (currentIndex - 1 + items.length) % items.length;
                    
                    items[nextIndex].focus();
                }
            }
        }
    });
}

// Agregar indicadores de foco visible mejorados
function enhanceFocusIndicators() {
    const style = document.createElement('style');
    style.id = 'accessibility-focus-styles';
    style.textContent = `
        /* Focus visible mejorado */
        *:focus-visible {
            outline: 3px solid #667eea;
            outline-offset: 2px;
            border-radius: 4px;
        }
        
        /* Skip link para navegación por teclado */
        .skip-link {
            position: absolute;
            top: -40px;
            left: 0;
            background: #667eea;
            color: white;
            padding: 8px 16px;
            text-decoration: none;
            z-index: 100000;
            border-radius: 0 0 4px 0;
        }
        
        .skip-link:focus {
            top: 0;
        }
        
        /* Indicador de carga para lectores de pantalla */
        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border-width: 0;
        }
        
        /* Mejorar contraste en modo de alto contraste */
        @media (prefers-contrast: high) {
            * {
                border-width: 2px !important;
            }
        }
    `;
    
    if (!document.getElementById('accessibility-focus-styles')) {
        document.head.appendChild(style);
    }
}

// Agregar skip link para navegación rápida
function addSkipLink() {
    if (document.getElementById('skip-to-main')) return;
    
    const skipLink = document.createElement('a');
    skipLink.href = '#main-content';
    skipLink.className = 'skip-link';
    skipLink.textContent = 'Saltar al contenido principal';
    skipLink.id = 'skip-to-main';
    document.body.insertBefore(skipLink, document.body.firstChild);
    
    // Agregar ID al contenido principal si no existe
    const main = document.querySelector('main, .main-container, .container');
    if (main && !main.id) {
        main.id = 'main-content';
    }
}

// Anunciar cambios dinámicos a lectores de pantalla
function announceToScreenReader(message, priority = 'polite') {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', priority);
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    // Remover después de un tiempo
    setTimeout(() => {
        announcement.remove();
    }, 1000);
}

// Mejorar labels de formularios
function enhanceFormLabels() {
    const inputs = document.querySelectorAll('input, select, textarea');
    
    inputs.forEach(input => {
        // Si no tiene aria-label ni está asociado con un label
        if (!input.getAttribute('aria-label') && !input.getAttribute('aria-labelledby')) {
            const id = input.id || `input-${Math.random().toString(36).substr(2, 9)}`;
            input.id = id;
            
            // Buscar label asociado
            const label = document.querySelector(`label[for="${id}"]`);
            if (label) {
                input.setAttribute('aria-labelledby', `label-${id}`);
                label.id = `label-${id}`;
            } else if (input.placeholder) {
                // Usar placeholder como aria-label si no hay label
                input.setAttribute('aria-label', input.placeholder);
            }
        }
        
        // Agregar aria-required si el campo es required
        if (input.required && !input.getAttribute('aria-required')) {
            input.setAttribute('aria-required', 'true');
        }
        
        // Agregar aria-invalid si hay errores
        if (input.hasAttribute('aria-invalid') && input.getAttribute('aria-invalid') === 'false') {
            // Mantener el estado actual
        } else if (input.classList.contains('error') || input.classList.contains('is-invalid')) {
            input.setAttribute('aria-invalid', 'true');
        }
    });
}

// Mejorar botones
function enhanceButtons() {
    const buttons = document.querySelectorAll('button, [role="button"]');
    
    buttons.forEach(button => {
        // Asegurar que los botones tengan texto accesible
        if (!button.getAttribute('aria-label') && !button.textContent.trim() && !button.getAttribute('aria-labelledby')) {
            const icon = button.querySelector('img, svg, [class*="icon"]');
            if (icon) {
                button.setAttribute('aria-label', button.title || 'Botón');
            }
        }
        
        // Agregar aria-disabled si está deshabilitado
        if (button.disabled) {
            button.setAttribute('aria-disabled', 'true');
        }
    });
}

// Inicializar mejoras de accesibilidad
function initAccessibility() {
    enhanceFocusIndicators();
    addSkipLink();
    initKeyboardNavigation();
    
    // Mejorar elementos al cargar
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            enhanceFormLabels();
            enhanceButtons();
        });
    } else {
        enhanceFormLabels();
        enhanceButtons();
    }
    
    // Mejorar elementos después de cambios dinámicos
    const observer = new MutationObserver(() => {
        enhanceFormLabels();
        enhanceButtons();
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}

// Inicializar al cargar
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAccessibility);
} else {
    initAccessibility();
}








