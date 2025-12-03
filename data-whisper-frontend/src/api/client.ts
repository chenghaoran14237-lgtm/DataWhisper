import axios from 'axios'
import { ElMessage } from 'element-plus'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 20000,
})

client.interceptors.response.use(
  (res) => res.data,
  (error) => {
    const msg = error.response?.data?.detail || '连接服务器失败'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)
export default client