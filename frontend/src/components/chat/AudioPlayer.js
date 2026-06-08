/**
 * 音频播放工具类
 * 用于播放数字人回复的语音
 * 支持播放 Base64 编码的音频片段
 */
export class AudioPlayer {
  constructor() {
    this.audioContext = null
    this.queue = []
    this.isPlaying = false
    this.currentAudio = null
  }

  /**
   * 初始化 AudioContext（需要用户交互后调用）
   */
  init() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)()
    }
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
      return
    }

    this.isPlaying = true
    const { base64Data, format } = this.queue.shift()

    try {
      // 方案 A：使用 Audio 元素（简单可靠）
      const audioUrl = `data:audio/${format};base64,${base64Data}`
      const audio = new Audio(audioUrl)
      this.currentAudio = audio

      await new Promise((resolve, reject) => {
        audio.onended = resolve
        audio.onerror = (e) => {
          console.warn('Audio 播放失败，跳过:', e)
          resolve() // 出错也继续播放下一个
        }
        audio.play().catch(reject)
      })

      this.currentAudio = null
    } catch (e) {
      console.warn('音频播放异常:', e)
    }

    // 播放下一个
    this._playNext()
  }

  /**
   * 停止播放并清空队列
   */
  stop() {
    this.queue = []
    this.isPlaying = false
    if (this.currentAudio) {
      this.currentAudio.pause()
      this.currentAudio = null
    }
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
  }
}
