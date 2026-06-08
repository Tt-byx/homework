/**
 * 语音录音工具类
 * 基于 MediaRecorder API 实现按住录音
 *
 * 使用方式：
 *   const recorder = new VoiceRecorder()
 *   await recorder.start()
 *   // ... 用户松开按钮
 *   const blob = await recorder.stop()
 */
export class VoiceRecorder {
  constructor() {
    this.mediaRecorder = null
    this.stream = null
    this.chunks = []
    this.isRecording = false
    this.startTime = 0
  }

  /**
   * 检查浏览器是否支持录音
   */
  static isSupported() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder)
  }

  /**
   * 开始录音
   * @returns {Promise<void>}
   */
  async start() {
    if (this.isRecording) return

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      })

      // 选择最佳的 MIME 类型
      const mimeType = this._getBestMimeType()
      this.mediaRecorder = new MediaRecorder(this.stream, {
        mimeType: mimeType,
      })

      this.chunks = []
      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          this.chunks.push(e.data)
        }
      }

      this.mediaRecorder.start(100) // 每 100ms 收集一块
      this.isRecording = true
      this.startTime = Date.now()

    } catch (error) {
      this._cleanup()
      if (error.name === 'NotAllowedError') {
        throw new Error('请允许麦克风权限后重试')
      } else if (error.name === 'NotFoundError') {
        throw new Error('未检测到麦克风设备')
      }
      throw error
    }
  }

  /**
   * 停止录音并返回音频 Blob
   * @returns {Promise<{blob: Blob, duration: number, format: string}>}
   */
  stop() {
    return new Promise((resolve, reject) => {
      if (!this.isRecording || !this.mediaRecorder) {
        resolve(null)
        return
      }

      this.mediaRecorder.onstop = () => {
        const duration = Date.now() - this.startTime
        const format = this._getFormat()
        const blob = new Blob(this.chunks, { type: this.mediaRecorder.mimeType })

        this._cleanup()
        resolve({ blob, duration, format })
      }

      this.mediaRecorder.onerror = (e) => {
        this._cleanup()
        reject(new Error('录音失败'))
      }

      this.isRecording = false
      this.mediaRecorder.stop()
    })
  }

  /**
   * 取消录音
   */
  cancel() {
    this.isRecording = false
    this.chunks = []
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop()
    }
    this._cleanup()
  }

  /**
   * 清理资源
   */
  _cleanup() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop())
      this.stream = null
    }
    this.mediaRecorder = null
    this.chunks = []
  }

  /**
   * 获取最佳 MIME 类型
   */
  _getBestMimeType() {
    const types = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4',
    ]
    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type
      }
    }
    return '' // 让浏览器选择默认
  }

  /**
   * 获取音频格式后缀
   */
  _getFormat() {
    const mime = this.mediaRecorder?.mimeType || ''
    if (mime.includes('webm')) return 'webm'
    if (mime.includes('ogg')) return 'ogg'
    if (mime.includes('mp4')) return 'mp4'
    return 'webm'
  }

  /**
   * 销毁实例
   */
  destroy() {
    this.cancel()
  }
}
