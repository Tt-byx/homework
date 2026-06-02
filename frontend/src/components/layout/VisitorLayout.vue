<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <el-container class="visitor-layout">
    <el-header class="visitor-header">
      <div class="header-left">
        <el-icon :size="24" color="#409EFF"><ChatDotRound /></el-icon>
        <span class="header-title">景区AI导游</span>
      </div>
      <div class="header-right">
        <el-button text @click="router.push('/admin')">管理后台</el-button>
      </div>
    </el-header>
    <el-main class="visitor-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<style scoped>
.visitor-layout {
  height: 100vh;
}

.visitor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e4e7ed;
  background: #fff;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.visitor-main {
  background: #f5f7fa;
  padding: 0;
  display: flex;
  justify-content: center;
}
</style>
