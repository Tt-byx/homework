<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useLive2D } from '@/live2d/useLive2D'

const emit = defineEmits(['ready', 'error'])
const canvasRef = ref(null)
const live2d = useLive2D()
const debugLog = ref([])

let pressTimer = null
let isLongPress = false
let returnTimer = null

function log(msg) {
  console.log('[Live2D]', msg)
  debugLog.value.push(msg)
  if (debugLog.value.length > 10) debugLog.value.shift()
}

function onMouseDown(e) {
  isLongPress = false
  clearTimeout(returnTimer)
  // 立即看向点击位置
  live2d.onTouchMoved(e)
  // 200ms 后仍按住 → 长按模式，持续跟随
  pressTimer = setTimeout(() => { isLongPress = true }, 200)
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

function onMouseMove(e) {
  if (isLongPress) {
    live2d.onTouchMoved(e)
  }
}

function onMouseUp() {
  clearTimeout(pressTimer)
  document.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('mouseup', onMouseUp)

  if (!isLongPress) {
    // 短按：在点击位置停留 800ms 后回正
    returnTimer = setTimeout(() => { live2d.resetLook() }, 800)
  } else {
    // 长按：立即回正
    live2d.resetLook()
  }
}

onMounted(() => {
  log('组件已挂载')
  if (!canvasRef.value) {
    log('❌ canvasRef 为空')
    return
  }
  log(`Canvas 尺寸: ${canvasRef.value.clientWidth}x${canvasRef.value.clientHeight}`)

  if (typeof Live2DCubismCore === 'undefined') {
    log('❌ Live2DCubismCore 未加载')
    emit('error', 'Cubism Core 未加载')
    return
  }
  log('✅ Live2DCubismCore 已加载')

  try {
    const ok = live2d.init(canvasRef.value)
    if (ok) {
      log('✅ Live2D 初始化成功')
      emit('ready')
    } else {
      log('❌ Live2D 初始化失败')
      emit('error', 'WebGL 初始化失败')
    }
  } catch (e) {
    log('❌ 异常: ' + e.message)
    emit('error', e.message)
  }

  // 绑定 mousedown 到 canvas（点击数字人才触发）
  document.addEventListener('mousedown', onMouseDown)
})

onUnmounted(() => {
  clearTimeout(pressTimer)
  clearTimeout(returnTimer)
  document.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('mouseup', onMouseUp)
  document.removeEventListener('mousedown', onMouseDown)
})

defineExpose({
  setLipSync: live2d.setLipSync,
  startLipSyncFromAnalyser: live2d.startLipSyncFromAnalyser,
  startTextLipSync: live2d.startTextLipSync,
  stopTextLipSync: live2d.stopTextLipSync,
  stopLipSync: live2d.stopLipSync,
  setExpression: live2d.setExpression,
  randomExpression: live2d.randomExpression,
  isReady: live2d.isReady,
  updateLookSensitivity: live2d.updateLookSensitivity,
  updateBreathIntensity: live2d.updateBreathIntensity,
})
</script>

<template>
  <div class="live2d-container">
    <canvas ref="canvasRef" class="live2d-canvas" />
    <div class="debug-overlay" v-if="debugLog.length > 0">
      <div v-for="(msg, i) in debugLog" :key="i" class="debug-line">{{ msg }}</div>
    </div>
    <slot />
  </div>
</template>

<style scoped>
.live2d-container {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
.live2d-canvas {
  display: block;
  width: 100%;
  height: 100%;
  cursor: pointer;
}
.debug-overlay {
  position: absolute;
  bottom: 8px;
  left: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.7);
  color: #0f0;
  font-size: 11px;
  font-family: monospace;
  padding: 6px 8px;
  border-radius: 6px;
  max-height: 150px;
  overflow-y: auto;
  z-index: 10;
  pointer-events: none;
}
.debug-line { line-height: 1.5; }
</style>