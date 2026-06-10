/**
 * 音频播放工具类
 * 使用 Web Audio API，支持 AnalyserNode 实时音频分析（用于口型同步）
 */
export class AudioPlayer {
  constructor() {
    this.audioContext = null
    this.analyser = null
    this.queue = []
    this.isPlaying = false
    this.currentSource = null

    // 回调钩子
    this.onPlayStart = null   // (analyser) => {}
    this.onPlayEnd = null     // () => {}
  }

  /**
   * 初始化 AudioContext（需要用户交互后调用）
   */
  init() {
    if (this.audioContext) return

    this.audioContext = new (window.AudioContext || window.webkitAudioContext)()

    // 创建 AnalyserNode 用于口型同步
    this.analyser = this.audioContext.createAnalyser()
    this.analyser.fftSize = 256
    this.analyser.smoothingTimeConstant = 0.5
    this.analyser.connect(this.audioContext.destination)
  }

  /**
   * 将 Base64 音频数据加入播放队列
   * @param {string} base64Data - Base64 编码的音频数据
   * @param {string} format - 音频格式 (wav/mp3)
   */
  enqueue(base64Data, format = 'wav') {
    this.queue.push({ base64Data, format })
    if (!this.isPlaying) {
      this._playNext()
    }
  }

  /**
   * 播放队列中的下一个音频
   */
  async _playNext() {
    if (this.queue.length === 0) {
      this.isPlaying = false
      this.onPlayEnd?.()
      return
    }

    this.isPlaying = true
    const { base64Data, format } = this.queue.shift()

    try {
      if (!this.audioContext) this.init()

      // Resume suspended context
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume()
      }

      // Base64 → ArrayBuffer
      const binaryStr = atob(base64Data)
      const bytes = new Uint8Array(binaryStr.length)
      for (let i = 0; i < binaryStr.length; i++) {
        bytes[i] = binaryStr.charCodeAt(i)
      }

      // 解码音频
      const audioBuffer = await this.audioContext.decodeAudioData(bytes.buffer)

      // 创建源节点
      const source = this.audioContext.createBufferSource()
      source.buffer = audioBuffer
      source.connect(this.analyser)

      this.currentSource = source

      // 通知开始播放（暴露 analyser 用于口型同步）
      this.onPlayStart?.(this.analyser)

      // 播放
      await new Promise((resolve) => {
        source.onended = () => {
          this.currentSource = null
          resolve()
        }
        source.start(0)
      })
    } catch (e) {
      console.warn('音频播放异常:', e)
      // 回退：使用 Audio 元素
      await this._fallbackPlay(base64Data, format)
    }

    // 播放下一个
    this._playNext()
  }

  /**
   * 回退方案：使用 Audio 元素（不支持 AnalyserNode）
   */
  async _fallbackPlay(base64Data, format) {
    try {
      const audioUrl = `data:audio/${format};base64,${base64Data}`
      const audio = new Audio(audioUrl)
      await new Promise((resolve) => {
        audio.onended = resolve
        audio.onerror = resolve
        audio.play().catch(resolve)
      })
    } catch (e) {
      // ignore
    }
  }

  /**
   * 停止播放并清空队列
   */
  stop() {
    this.queue = []
    this.isPlaying = false
    if (this.currentSource) {
      try { this.currentSource.stop() } catch (e) { /* ignore */ }
      this.currentSource = null
    }
    this.onPlayEnd?.()
  }

  /**
   * 销毁
   */
  destroy() {
    this.stop()
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }
    this.analyser = null
  }
}
