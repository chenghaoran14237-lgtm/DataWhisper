<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import type { ChartSpecLine } from '../api/types'

const props = defineProps<{
  spec: ChartSpecLine
}>()

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const initChart = () => {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value, undefined, { renderer: 'svg' })
  
  const option: echarts.EChartsOption = {
    backgroundColor: 'transparent', // 透明背景，透出卡片底色
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(26, 27, 38, 0.9)',
      borderColor: '#5e7ce2',
      textStyle: { color: '#fff' }
    },
    grid: {
      top: '15%', left: '3%', right: '4%', bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: props.spec.x.values,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#a0aec0' },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }, // 极淡的网格线
      axisLabel: { color: '#a0aec0' }
    },
    series: props.spec.series.map(s => ({
      name: s.name,
      type: 'line',
      data: s.values,
      smooth: true, // 平滑曲线
      symbol: 'circle',
      symbolSize: 6,
      itemStyle: { color: '#5e7ce2', borderColor: '#fff', borderWidth: 2 },
      lineStyle: {
        width: 3,
        shadowColor: 'rgba(94, 124, 226, 0.5)', // 霓虹光晕
        shadowBlur: 10
      },
      areaStyle: {
        // 渐变填充，增加科技感
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(94, 124, 226, 0.3)' },
          { offset: 1, color: 'rgba(94, 124, 226, 0.0)' }
        ])
      }
    }))
  }
  
  chartInstance.setOption(option)
}

// 监听窗口大小变化，自动调整图表
const handleResize = () => chartInstance?.resize()

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<template>
  <div class="chart-card">
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<style scoped>
.chart-card {
  margin-top: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}
.chart-container {
  width: 100%;
  height: 300px; /* 固定高度，确保渲染 */
}
</style>