// Ejecutar en la consola del navegador
if (typeof deployToProduction === 'function') {
    deployToProduction();
    console.log('✅ Función deployToProduction ejecutada');
} else {
    console.error('❌ Función deployToProduction no encontrada');
}
