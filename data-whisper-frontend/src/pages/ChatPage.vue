<script setup lang="ts">
import { onMounted, ref, nextTick } from 'vue'
import { useSessionStore } from '../stores/session'
import { listMessages, chatExcel } from '../api/excel'
import type { ChatMessage } from '../api/types'
import { Position, Promotion, RefreshRight } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import ChartCard from '../components/ChartCard.vue' // <--- 1. 引入组件

const router = useRouter(); const sessionStore = useSessionStore()
const messages = ref<ChatMessage[]>([]); const inputValue = ref(''); const isLoading = ref(false)
const msgContainer = ref<HTMLElement | null>(null)

const initChat = async () => {
  if (!sessionStore.sessionId) return;
  const res = await listMessages(sessionStore.sessionId)
  messages.value = res.items
  scrollToBottom()
}

const handleSend = async () => {
  const content = inputValue.value.trim()
  if (!content || !sessionStore.sessionId || !sessionStore.uploadId) return
  messages.value.push({ id: Date.now().toString(), role: 'user', content, created_at: '', artifacts: [] })
  inputValue.value = ''; isLoading.value = true; scrollToBottom()
  try {
    const res = await chatExcel({ session_id: sessionStore.sessionId, upload_id: sessionStore.uploadId, message: content })
    messages.value.push({ id: Date.now().toString(), role: 'assistant', content: res.reply, created_at: '', artifacts: res.artifacts || [] })
  } catch (e) {
    messages.value.push({ id: 'err', role: 'assistant', content: '⚠️ 思考中断，请重试', created_at: '', artifacts: [] })
  } finally { isLoading.value = false; scrollToBottom() }
}

const scrollToBottom = () => nextTick(() => { if (msgContainer.value) msgContainer.value.scrollTop = msgContainer.value.scrollHeight })
const handleNewSession = () => { sessionStore.clearSession(); router.push('/') }
onMounted(initChat)
</script>

<template>
  <div class="chat-layout">
    <header class="chat-header">
      <div class="file-info">
        <span class="file-name">{{ sessionStore.filename }}</span>
        <span class="file-meta" v-if="sessionStore.profile">
          {{ sessionStore.profile.rows }} 行 · {{ sessionStore.profile.cols }} 列
        </span>
      </div>
      <el-button size="small" circle :icon="RefreshRight" @click="handleNewSession" title="新会话" />
    </header>

    <div class="messages-area" ref="msgContainer">
      <div v-for="msg in messages" :key="msg.id" class="message-row" :class="{ 'is-user': msg.role === 'user' }">
        <div class="bubble">
          <div class="bubble-text">{{ msg.content }}</div>
          
          <div v-if="msg.artifacts && msg.artifacts.length > 0" class="artifacts-wrapper">
            <template v-for="(art, idx) in msg.artifacts" :key="idx">
              <ChartCard v-if="art.kind === 'chart'" :spec="art.spec" />
            </template>
          </div>
        </div>
      </div>
      <div v-if="isLoading" class="message-row"><div class="bubble typing"><span>●</span><span>●</span><span>●</span></div></div>
    </div>

    <div class="input-area">
      <div class="input-wrapper">
        <el-input v-model="inputValue" placeholder="Ask DataWhisper..." @keyup.enter="handleSend" class="chat-input">
           <template #prefix><el-icon><Position /></el-icon></template>
        </el-input>
        <el-button type="primary" :icon="Promotion" circle @click="handleSend" :loading="isLoading" class="send-btn"/>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 保持原有样式，增加 specifics */
.chat-layout { height: 100vh; display: flex; flex-direction: column; background: var(--dw-bg-dark); }
.chat-header { height: 50px; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: space-between; padding: 0 20px; background: rgba(26,27,38,0.95); }
.file-name { font-weight: 600; color: white; margin-right: 12px; }
.file-meta { font-size: 12px; color: var(--dw-text-sub); background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px; }

.messages-area { flex: 1; overflow-y: auto; padding: 20px; scroll-behavior: smooth; }
.message-row { display: flex; margin-bottom: 24px; } /* 增加间距 */
.message-row.is-user { justify-content: flex-end; }

.bubble { max-width: 75%; padding: 12px 16px; border-radius: 12px; font-size: 15px; line-height: 1.6; color: var(--dw-text-main); background: var(--dw-card-bg); border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.is-user .bubble { background: var(--dw-accent-blue); color: white; border: none; }

.artifacts-wrapper { margin-top: 12px; }

.input-area { padding: 20px; background: var(--dw-bg-dark); }
.input-wrapper { max-width: 800px; margin: 0 auto; display: flex; gap: 12px; }
.chat-input :deep(.el-input__wrapper) { background-color: var(--dw-card-bg); box-shadow: none; border: 1px solid rgba(255,255,255,0.1); border-radius: 24px; padding: 8px 20px; }
.chat-input :deep(.el-input__inner) { color: white; }
.typing span { animation: blink 1.4s infinite both; margin: 0 2px; display: inline-block; }
.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0% { opacity: 0.2; } 20% { opacity: 1; } 100% { opacity: 0.2; } }
</style>