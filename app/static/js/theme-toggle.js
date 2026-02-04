/**
 * Toggle tema claro/oscuro. Solo manual: botón alterna dark/light y persiste en localStorage("theme").
 * Sin detección de OS; init en <head> usa localStorage("theme") o default "dark".
 */
(function () {
  var STORAGE_KEY = 'theme';
  var THEME_DARK = 'dark';
  var THEME_LIGHT = 'light';

  function getSavedTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return null;
    }
  }

  function saveTheme(theme) {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {}
  }

  function applyTheme(theme) {
    var root = document.documentElement;
    if (theme === THEME_LIGHT || theme === THEME_DARK) {
      root.setAttribute('data-theme', theme);
    } else {
      root.removeAttribute('data-theme');
    }
  }

  function updateToggleLabel(theme) {
    var labelText = theme === THEME_LIGHT ? 'Oscuro' : 'Claro';
    document.querySelectorAll('.theme-toggle-label').forEach(function (label) {
      label.textContent = labelText;
    });
  }

  function getCurrentTheme() {
    var t = document.documentElement.getAttribute('data-theme');
    return t === THEME_LIGHT || t === THEME_DARK ? t : THEME_DARK;
  }

  function onToggleClick() {
    var next = getCurrentTheme() === THEME_DARK ? THEME_LIGHT : THEME_DARK;
    applyTheme(next);
    saveTheme(next);
    updateToggleLabel(next);
  }

  function init() {
    var saved = getSavedTheme();
    if (saved === THEME_LIGHT || saved === THEME_DARK) {
      applyTheme(saved);
    }
    /* When no saved theme, <head> script already set data-theme="dark"; do not overwrite */
    updateToggleLabel(getCurrentTheme());

    /* Delegación: un solo listener en document para que funcione aunque el DOM cambie */
    document.addEventListener('click', function (e) {
      if (e.target && e.target.closest && e.target.closest('.theme-toggle')) {
        e.preventDefault();
        onToggleClick();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
