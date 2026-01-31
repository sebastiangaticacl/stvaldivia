/**
 * 🎨 Utilidades JavaScript Profesionales BIMBA
 * Funciones reutilizables para mejor UX
 */

// --- LOADING STATES ---
const LoadingManager = {
  show(message = 'Cargando...') {
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.id = 'global-loading';
    overlay.innerHTML = `
      <div class="loading-content">
        <div class="loading-spinner loading-spinner-lg"></div>
        <p>${message}</p>
      </div>
    `;
    document.body.appendChild(overlay);
    document.body.style.overflow = 'hidden';
  },

  hide() {
    const overlay = document.getElementById('global-loading');
    if (overlay) {
      overlay.style.animation = 'fadeOut 0.2s ease-out';
      setTimeout(() => {
        overlay.remove();
        document.body.style.overflow = '';
      }, 200);
    }
  }
};

// --- NOTIFICACIONES MEJORADAS ---
const NotificationManager = {
  show(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} animate-slide-down`;
    notification.setAttribute('role', 'alert');
    notification.setAttribute('aria-live', 'polite');
    
    const icons = {
      success: '✅',
      error: '❌',
      warning: '⚠️',
      info: 'ℹ️'
    };
    
    notification.innerHTML = `
      <span class="alert-icon" aria-hidden="true">${icons[type] || icons.info}</span>
      <div class="alert-content">
        <div class="alert-message">${message}</div>
      </div>
      <button class="alert-close" onclick="this.parentElement.remove()" aria-label="Cerrar notificación">
        ×
      </button>
    `;
    
    // Agregar al contenedor de notificaciones
    let container = document.getElementById('notifications-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'notifications-container';
      container.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        z-index: 10000;
        max-width: 400px;
        width: 100%;
      `;
      document.body.appendChild(container);
    }
    
    container.appendChild(notification);
    
    // Auto-remover después de la duración
    if (duration > 0) {
      setTimeout(() => {
        notification.style.animation = 'fadeOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
      }, duration);
    }
    
    return notification;
  },

  success(message, duration = 5000) {
    return this.show(message, 'success', duration);
  },

  error(message, duration = 7000) {
    return this.show(message, 'error', duration);
  },

  warning(message, duration = 6000) {
    return this.show(message, 'warning', duration);
  },

  info(message, duration = 5000) {
    return this.show(message, 'info', duration);
  }
};

// --- VALIDACIÓN DE FORMULARIOS ---
const FormValidator = {
  validate(form) {
    const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
    let isValid = true;
    const errors = [];

    inputs.forEach(input => {
      const error = this.validateField(input);
      if (error) {
        isValid = false;
        errors.push(error);
        this.showFieldError(input, error);
      } else {
        this.clearFieldError(input);
      }
    });

    return { isValid, errors };
  },

  validateField(field) {
    const value = field.value.trim();
    const type = field.type;
    const required = field.hasAttribute('required');

    // Validar campo requerido
    if (required && !value) {
      return `${this.getFieldLabel(field)} es requerido`;
    }

    // Validar email
    if (type === 'email' && value) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(value)) {
        return 'Email inválido';
      }
    }

    // Validar URL
    if (type === 'url' && value) {
      try {
        new URL(value);
      } catch {
        return 'URL inválida';
      }
    }

    // Validar longitud mínima
    const minLength = field.getAttribute('minlength');
    if (minLength && value.length < parseInt(minLength)) {
      return `Mínimo ${minLength} caracteres`;
    }

    // Validar longitud máxima
    const maxLength = field.getAttribute('maxlength');
    if (maxLength && value.length > parseInt(maxLength)) {
      return `Máximo ${maxLength} caracteres`;
    }

    // Validar patrón
    const pattern = field.getAttribute('pattern');
    if (pattern && value) {
      const regex = new RegExp(pattern);
      if (!regex.test(value)) {
        return field.getAttribute('data-pattern-error') || 'Formato inválido';
      }
    }

    return null;
  },

  getFieldLabel(field) {
    const label = field.closest('.form-group')?.querySelector('label');
    return label?.textContent?.replace('*', '').trim() || field.name || 'Este campo';
  },

  showFieldError(field, message) {
    this.clearFieldError(field);
    
    field.classList.add('error');
    field.setAttribute('aria-invalid', 'true');
    
    const errorElement = document.createElement('div');
    errorElement.className = 'field-error';
    errorElement.textContent = message;
    errorElement.setAttribute('role', 'alert');
    errorElement.style.cssText = `
      color: var(--danger);
      font-size: var(--text-sm);
      margin-top: var(--space-1);
      display: flex;
      align-items: center;
      gap: var(--space-1);
    `;
    
    field.parentElement.appendChild(errorElement);
  },

  clearFieldError(field) {
    field.classList.remove('error');
    field.removeAttribute('aria-invalid');
    const errorElement = field.parentElement.querySelector('.field-error');
    if (errorElement) {
      errorElement.remove();
    }
  }
};

// --- DEBOUNCE Y THROTTLE ---
const Debounce = {
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  throttle(func, limit) {
    let inThrottle;
    return function(...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }
};

// --- UTILIDADES DE ACCESIBILIDAD ---
const Accessibility = {
  // Manejar navegación por teclado
  trapFocus(element) {
    const focusableElements = element.querySelectorAll(
      'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    element.addEventListener('keydown', (e) => {
      if (e.key === 'Tab') {
        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            lastElement.focus();
            e.preventDefault();
          }
        } else {
          if (document.activeElement === lastElement) {
            firstElement.focus();
            e.preventDefault();
          }
        }
      }
      
      if (e.key === 'Escape') {
        element.dispatchEvent(new CustomEvent('close'));
      }
    });
  },

  // Anunciar cambios a lectores de pantalla
  announce(message, priority = 'polite') {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', priority);
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'visually-hidden';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    setTimeout(() => {
      announcement.remove();
    }, 1000);
  }
};

// --- UTILIDADES DE PERFORMANCE ---
const Performance = {
  // Lazy load imágenes
  lazyLoadImages() {
    if ('IntersectionObserver' in window) {
      const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            if (img.dataset.src) {
              img.src = img.dataset.src;
              img.removeAttribute('data-src');
              img.classList.add('loaded');
              observer.unobserve(img);
            }
          }
        });
      });

      document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
      });
    }
  },

  // Preload recursos críticos
  preloadResource(href, as = 'style') {
    const link = document.createElement('link');
    link.rel = 'preload';
    link.href = href;
    link.as = as;
    document.head.appendChild(link);
  }
};

// --- INICIALIZACIÓN ---
document.addEventListener('DOMContentLoaded', () => {
  // Lazy load imágenes
  Performance.lazyLoadImages();
  
  // Agregar contenedor de notificaciones si no existe
  if (!document.getElementById('notifications-container')) {
    const container = document.createElement('div');
    container.id = 'notifications-container';
    container.style.cssText = `
      position: fixed;
      top: 80px;
      right: 20px;
      z-index: 10000;
      max-width: 400px;
      width: 100%;
    `;
    document.body.appendChild(container);
  }
  
  // Validar formularios automáticamente
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', (e) => {
      const validation = FormValidator.validate(form);
      if (!validation.isValid) {
        e.preventDefault();
        NotificationManager.error('Por favor, corrige los errores en el formulario');
        validation.errors.forEach(error => {
          NotificationManager.warning(error);
        });
      }
    });
    
    // Validación en tiempo real
    form.querySelectorAll('input, textarea, select').forEach(field => {
      field.addEventListener('blur', () => {
        FormValidator.validateField(field);
      });
    });
  });
});

// Exportar para uso global (solo si no existe)
if (!window.LoadingManager) {
    window.LoadingManager = LoadingManager;
}
if (!window.NotificationManager) {
    window.NotificationManager = NotificationManager;
}
if (!window.FormValidator) {
    window.FormValidator = FormValidator;
}
if (!window.Debounce) {
    window.Debounce = Debounce;
}
if (!window.Accessibility) {
    window.Accessibility = Accessibility;
}
if (!window.Performance) {
    window.Performance = Performance;
}
