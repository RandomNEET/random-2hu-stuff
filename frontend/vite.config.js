import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  build: {
    // Set more reasonable chunk size warning limit
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // Manual chunk configuration
        manualChunks: {
          // Vue core libraries
          'vue-vendor': ['vue', 'vue-router'],
          // UI framework (Vuetify is large, separate chunk)
          'vuetify-vendor': ['vuetify']
        },
        // Optimize file naming
        chunkFileNames: 'js/[name]-[hash].js',
        entryFileNames: 'js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name.split('.')
          const extType = info[info.length - 1]
          if (/\.(mp4|webm|ogg|mp3|wav|flac|aac)(\?.*)?$/i.test(assetInfo.name)) {
            return `media/[name]-[hash].${extType}`
          }
          if (/\.(png|jpe?g|gif|svg)(\?.*)?$/i.test(assetInfo.name)) {
            return `img/[name]-[hash].${extType}`
          }
          if (/\.(woff2?|eot|ttf|otf)(\?.*)?$/i.test(assetInfo.name)) {
            return `fonts/[name]-[hash].${extType}`
          }
          return `assets/[name]-[hash].${extType}`
        }
      }
    },
    // Enable CSS code splitting
    cssCodeSplit: true
  },
  // Development server optimization
  server: {
    hmr: {
      overlay: false
    }
  }
})
