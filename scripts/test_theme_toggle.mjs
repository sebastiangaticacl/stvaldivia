#!/usr/bin/env node
/**
 * Prueba del toggle de tema: abre la app, fuerza light y comprueba estilos.
 * Uso: node scripts/test_theme_toggle.mjs
 * Requiere: servidor en http://127.0.0.1:5001
 */
import { chromium } from 'playwright';

const BASE = 'http://127.0.0.1:5001';

async function main() {
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    // 1) Cargar página
    const res = await page.goto(BASE, { waitUntil: 'networkidle', timeout: 10000 });
    if (!res || res.status() !== 200) {
      console.log('ERROR: No se pudo cargar', BASE, 'Status:', res?.status());
      process.exit(1);
    }

    // 2) Estado inicial (dark por defecto)
    const bgBefore = await page.evaluate(() => {
      const html = document.documentElement;
      const body = document.body;
      return {
        dataTheme: html.getAttribute('data-theme'),
        bodyBg: getComputedStyle(body).backgroundColor,
        bodyColor: getComputedStyle(body).color,
      };
    });
    console.log('Antes (esperado dark):', JSON.stringify(bgBefore, null, 2));

    // 3) Forzar tema light vía JS (como hace el toggle)
    await page.evaluate(() => {
      document.documentElement.setAttribute('data-theme', 'light');
    });

    // Dar tiempo a que el CSS se recompile
    await page.waitForTimeout(300);

    // 4) Leer estilos después de light
    const bgAfter = await page.evaluate(() => {
      const html = document.documentElement;
      const body = document.body;
      const bodyStyle = getComputedStyle(body);
      const htmlStyle = getComputedStyle(html);
      return {
        dataTheme: html.getAttribute('data-theme'),
        bodyBackgroundColor: bodyStyle.backgroundColor,
        bodyColor: bodyStyle.color,
        htmlBackgroundColor: htmlStyle.backgroundColor,
      };
    });
    console.log('Después de setAttribute("light"):', JSON.stringify(bgAfter, null, 2));

    // 5) Criterio de éxito: body con fondo claro (rgb(241, 245, 249) = #f1f5f9)
    const lightBg = 'rgb(241, 245, 249)';
    const bodyOk = bgAfter.bodyBackgroundColor === lightBg || bgAfter.bodyBackgroundColor.includes('241');
    const htmlOk = bgAfter.htmlBackgroundColor === lightBg || bgAfter.htmlBackgroundColor.includes('241');

    if (bodyOk || htmlOk) {
      console.log('OK: Tema light se aplica (fondo claro detectado).');
    } else {
      console.log('FALLO: Body/HTML no tienen fondo claro. Body bg:', bgAfter.bodyBackgroundColor);
      // Guardar screenshot para diagnóstico
      await page.screenshot({ path: 'scripts/theme_test_screenshot.png' });
      console.log('Captura guardada en scripts/theme_test_screenshot.png');
    }

    // 6) Probar click en el botón del header
    const btn = await page.locator('#theme-toggle').first();
    if (await btn.count() > 0) {
      await btn.click();
      await page.waitForTimeout(200);
      const afterClick = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
      console.log('Después de click en #theme-toggle, data-theme:', afterClick);
    } else {
      console.log('No se encontró #theme-toggle en la página');
    }
  } catch (e) {
    console.error('Error:', e.message);
    process.exit(1);
  } finally {
    if (browser) await browser.close();
  }
}

main();
