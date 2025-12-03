import { createRouter, createWebHistory } from 'vue-router'
import UploadPage from '../pages/UploadPage.vue'
import ChatPage from '../pages/ChatPage.vue'
import { useSessionStore } from '../stores/session'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'upload', component: UploadPage },
    { 
      path: '/chat', name: 'chat', component: ChatPage,
      beforeEnter: (to, from, next) => {
        const store = useSessionStore()
        if (!store.sessionId) next({ name: 'upload' })
        else next()
      }
    },
  ],
})
export default router