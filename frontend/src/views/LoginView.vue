<template>
  <div class="login-screen">
    <form class="login-card" @submit.prevent="submit">
      <div class="login-card__logo">
        <span class="login-card__logo-icon">⬡</span>
        <div>
          <div class="login-card__title">АТЛАС</div>
          <div class="login-card__sub">Вход в систему</div>
        </div>
      </div>

      <label class="login-card__label" for="password">Пароль</label>
      <input
        id="password"
        v-model="password"
        type="password"
        class="login-card__input"
        placeholder="Введите пароль"
        autofocus
        :disabled="loading"
      />

      <div v-if="error" class="login-card__error">{{ error }}</div>

      <button type="submit" class="login-card__submit" :disabled="loading || !password">
        {{ loading ? 'Проверка…' : 'Войти' }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { authApi } from '@/utils/api'
import { invalidateAuthCache } from '@/router'

const password = ref('')
const loading = ref(false)
const error = ref('')
const router = useRouter()
const route = useRoute()

async function submit() {
  if (!password.value) return
  loading.value = true
  error.value = ''
  try {
    await authApi.login(password.value)
    invalidateAuthCache()
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch (e) {
    error.value = e.message || 'Не удалось войти'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-screen {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--c-bg);
}
.login-card {
  width: 340px;
  padding: 32px 28px;
  border-radius: 14px;
  background: var(--c-bg2);
  border: 1px solid var(--c-border);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.login-card__logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.login-card__logo-icon {
  font-size: 30px;
  color: var(--c-accent);
}
.login-card__title {
  font-size: 18px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--c-accent), var(--c-accent2));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 2px;
}
.login-card__sub {
  font-size: 12px;
  color: var(--c-text3);
}
.login-card__label {
  font-size: 12px;
  color: var(--c-text2);
  margin-top: 4px;
}
.login-card__input {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  color: var(--c-text);
  font-size: 14px;
}
.login-card__input:focus {
  outline: none;
  border-color: var(--c-accent);
}
.login-card__error {
  font-size: 12px;
  color: var(--c-red);
}
.login-card__submit {
  margin-top: 8px;
  padding: 10px 14px;
  border-radius: 8px;
  border: none;
  background: var(--c-accent);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}
.login-card__submit:disabled {
  opacity: 0.5;
  cursor: default;
}
</style>
