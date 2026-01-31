// Configuración del agente. Usa solo variables de entorno para credenciales sensibles.
const toInt = (value, fallback) => {
  const parsed = parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
};

module.exports = {
  port: toInt(process.env.PORT, 5005),
  env: process.env.GETNET_ENV || 'demo', // demo | prod
  saleTimeoutMs: toInt(process.env.GETNET_SALE_TIMEOUT_MS, 120_000),
  retryAttempts: toInt(process.env.GETNET_RETRY_ATTEMPTS, 1),
  // Datos específicos del SDK. Reemplazar/ajustar según manual oficial.
  terminal: {
    commerceId: process.env.GETNET_COMMERCE_ID || '',
    terminalId: process.env.GETNET_TERMINAL_ID || '',
    device: process.env.GETNET_DEVICE_PORT || 'COM3', // Puerto USB-Serial típico en Windows
    configPath: process.env.GETNET_CONFIG_PATH || '',
    additionalParams: process.env.GETNET_ADDITIONAL_PARAMS || ''
  }
};


