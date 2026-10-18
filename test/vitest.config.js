import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';

const frontendRequire = createRequire(new URL('../frontend/package.json', import.meta.url));

export default defineConfig({
  root: fileURLToPath(new URL('./frontend', import.meta.url)),
  cacheDir: fileURLToPath(new URL('./.cache/vitest', import.meta.url)),
  resolve: {
    alias: [
      { find: '@', replacement: fileURLToPath(new URL('../frontend/src', import.meta.url)) },
      // Lifecycle tests and application composables must use the same Vue instance.
      { find: /^vue$/, replacement: frontendRequire.resolve('vue/dist/vue.runtime.esm-bundler.js') },
    ],
  },
  test: { include: ['unit/**/*.test.js'] },
});
