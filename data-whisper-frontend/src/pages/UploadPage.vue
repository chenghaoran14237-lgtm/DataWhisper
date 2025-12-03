<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { UploadFilled, Loading } from '@element-plus/icons-vue'
import { uploadExcel } from '../api/excel'
import { useSessionStore } from '../stores/session'

const router = useRouter()
const sessionStore = useSessionStore()
const isUploading = ref(false)

const handleCustomUpload = async (options: any) => {
  isUploading.value = true
  try {
    const res = await uploadExcel(options.file, sessionStore.sessionId || undefined)
    sessionStore.saveSessionInfo(res.session_id, res.upload_id, res.filename, res.profile)
    setTimeout(() => router.push('/chat'), 800)
  } catch (e) {
    console.error(e)
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <div class="upload-page">
    <div class="hero-content">
      <div class="logo-wrapper">
        <img src="/logo.png" alt="DataWhisper" class="hero-logo" />
        <div class="pulse-ring"></div>
      </div>
      <h1 class="title">DataWhisper <span class="tag">AI</span></h1>
      <p class="subtitle">让数据开口说话，在此刻。</p>

      <div class="upload-card">
        <el-upload
          drag action="" :http-request="handleCustomUpload" :show-file-list="false"
          accept=".xlsx" class="custom-uploader" :disabled="isUploading"
        >
          <div class="upload-inner">
            <template v-if="isUploading">
              <el-icon class="is-loading upload-icon"><Loading /></el-icon>
              <div class="upload-text">正在解析数据神经...</div>
            </template>
            <template v-else>
              <el-icon class="upload-icon"><UploadFilled /></el-icon>
              <div class="upload-text">拖拽 Excel 文件至此，或 <em>点击上传</em></div>
            </template>
          </div>
        </el-upload>
      </div>
    </div>
  </div>
</template>

<style scoped>
.upload-page {
  height: 100vh;
  display: flex; justify-content: center; align-items: center;
  background: radial-gradient(circle at center, #2a2d3e 0%, #1a1b26 100%);
}
.hero-content { text-align: center; animation: fadeInUp 0.8s ease-out; }
.logo-wrapper { position: relative; display: inline-block; margin-bottom: 24px; }
.hero-logo { width: 100px; position: relative; z-index: 2; filter: drop-shadow(0 0 15px var(--dw-accent-glow)); }
.pulse-ring {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  width: 100px; height: 100px; border-radius: 50%;
  border: 2px solid var(--dw-accent-blue); opacity: 0; animation: pulse 2s infinite;
}
.title { font-size: 3rem; font-weight: 700; margin: 0; color: white; }
.tag { font-size: 1rem; background: var(--dw-accent-blue); padding: 2px 8px; border-radius: 4px; vertical-align: middle; margin-left: 8px; color: white;}
.subtitle { color: var(--dw-text-sub); margin-bottom: 48px; font-size: 1.1rem; }
.upload-card {
  width: 480px; margin: 0 auto; background: var(--dw-card-bg);
  border-radius: 16px; padding: 8px; box-shadow: 0 20px 40px rgba(0,0,0,0.3);
}
.custom-uploader :deep(.el-upload-dragger) {
  background: transparent; border: 2px dashed rgba(255,255,255,0.1); border-radius: 12px; height: 200px;
  display: flex; flex-direction: column; justify-content: center; align-items: center;
}
.custom-uploader :deep(.el-upload-dragger:hover) { border-color: var(--dw-accent-blue); background: rgba(94,124,226,0.05); }
.upload-icon { font-size: 48px; color: var(--dw-text-sub); margin-bottom: 16px; }
.upload-text { color: var(--dw-text-sub); }
.upload-text em { color: var(--dw-accent-blue); font-style: normal; }
@keyframes pulse { 0% { transform: translate(-50%,-50%) scale(1); opacity: 0.6; } 100% { transform: translate(-50%,-50%) scale(1.5); opacity: 0; } }
@keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
</style>