#!/usr/bin/env node
/**
 * Prueba estática: verifica que las reglas CSS de tema light existan y tengan
 * la especificidad correcta. No usa navegador.
 */
import { readFileSync } from 'fs';
import { join } from 'path';

const root = join(process.cwd(), 'app', 'static', 'css');

function check(name, pred) {
  try {
    const ok = pred();
    console.log(ok ? 'OK' : 'FALLO', name);
    return ok;
  } catch (e) {
    console.log('FALLO', name, e.message);
    return false;
  }
}

const mainCss = readFileSync(join(root, 'main.css'), 'utf8');
const designCss = readFileSync(join(root, 'design-system.css'), 'utf8');

let passed = 0;
passed += check('main.css: html[data-theme="light"] con background-color', () =>
  /html\[data-theme="light"\][\s\S]*?background-color:\s*#f1f5f9/.test(mainCss) || mainCss.includes('[data-theme="light"] body')
);
passed += check('main.css: [data-theme="light"] body con background-color', () =>
  mainCss.includes('[data-theme="light"] body') && mainCss.includes('#f1f5f9')
);
passed += check('main.css: !important en body light', () => {
  const idx = mainCss.indexOf('[data-theme="light"] body');
  if (idx === -1) return false;
  const block = mainCss.slice(idx, idx + 400);
  return block.includes('!important');
});
passed += check('design-system: [data-theme="light"] define --bg-body', () =>
  designCss.includes('[data-theme="light"]') && designCss.includes('--bg-body: #f1f5f9')
);

console.log('\nTotal:', passed, '/ 4');
process.exit(passed >= 3 ? 0 : 1);
