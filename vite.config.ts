import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  build: {
    lib: {
      entry: resolve(__dirname, 'src/web_app/static/src/main.ts'),
      name: 'main',
      formats: ['es'],
      fileName: () => 'main.js'
    },
    outDir: resolve(__dirname, 'src/web_app/static/dist'),
    emptyOutDir: true,
    rollupOptions: {
      output: {
        assetFileNames: '[name][extname]'
      }
    }
  }
});
