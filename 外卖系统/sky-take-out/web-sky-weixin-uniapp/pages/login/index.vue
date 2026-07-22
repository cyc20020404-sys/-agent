<template>
  <view class="login-page">
    <view class="login-shell">
      <view class="back-button" @click="goBack">‹</view>
      <view class="brand-mark">苍</view>
      <view class="title">登录苍穹外卖</view>
      <view class="subtitle">登录后可同步购物车、管理地址并提交订单</view>

      <view class="form-card">
        <view class="field-label">手机号</view>
        <input
          v-model.trim="phone"
          class="field-input"
          type="number"
          maxlength="11"
          placeholder="请输入手机号"
        />

        <view class="field-label password-label">密码</view>
        <input
          v-model="password"
          class="field-input"
          type="text"
          password
          maxlength="32"
          placeholder="请输入密码"
          @confirm="submitLogin"
        />

        <button class="login-button" :disabled="submitting" @click="submitLogin">
          {{ submitting ? '登录中...' : '登录并继续结算' }}
        </button>

        <view class="demo-account">
          <view class="demo-title">本地测试账号</view>
          <view>手机号：13800138000</view>
          <view>密码：123456</view>
        </view>
      </view>

      <view class="security-tip">密码经过不可逆哈希保存，前端只保存登录令牌。</view>
    </view>
  </view>
</template>

<script>
import { h5Login, newAddShoppingCartAdd, getShoppingCartList } from '../api/api.js'
import { mapMutations } from 'vuex'

export default {
  data() {
    return {
      phone: '13800138000',
      password: '123456',
      redirect: '/pages/order/index',
      submitting: false,
    }
  },
  onLoad(options) {
    if (options && options.redirect) {
      this.redirect = decodeURIComponent(options.redirect)
    }
  },
  methods: {
    ...mapMutations([
      'setToken',
      'setBaseUserInfo',
      'setDeliveryFee',
      'setShopInfo',
      'initdishListMut',
    ]),
    goBack() {
      uni.navigateBack()
    },
    async mergeGuestCart() {
      const cart = uni.getStorageSync('sky-h5-guest-cart')
      if (Array.isArray(cart) && cart.length > 0) {
        for (const row of cart) {
          const params = {
            dishFlavor: row.dishFlavor || null,
          }
          if (row.dishId) params.dishId = row.dishId
          if (row.setmealId) params.setmealId = row.setmealId
          const count = Math.max(1, Number(row.number) || 1)
          for (let index = 0; index < count; index += 1) {
            await newAddShoppingCartAdd(params)
          }
        }
        uni.removeStorageSync('sky-h5-guest-cart')
      }

      const serverCart = await getShoppingCartList({})
      this.initdishListMut(Array.isArray(serverCart.data) ? serverCart.data : [])
    },
    async submitLogin() {
      if (this.submitting) return
      if (!/^1\d{10}$/.test(this.phone)) {
        uni.showToast({ title: '请输入正确的手机号', icon: 'none' })
        return
      }
      if (!this.password) {
        uni.showToast({ title: '请输入密码', icon: 'none' })
        return
      }

      this.submitting = true
      try {
        const result = await h5Login({
          phone: this.phone,
          password: this.password,
        })
        const user = result.data
        const baseUserInfo = {
          id: user.id,
          nickName: user.name || `用户${user.id}`,
          avatarUrl: user.avatar || '',
          phone: user.phone,
        }

        this.setToken(user.token)
        this.setBaseUserInfo(baseUserInfo)
        const deliveryFee = Number(user.deliveryFee || 0)
        const shopInfo = {
          shopName: user.shopName,
          shopAddress: user.shopAddress,
          description: user.description,
          shopId: user.shopId,
        }
        this.setDeliveryFee(deliveryFee)
        this.setShopInfo(shopInfo)
        uni.setStorageSync('token', user.token)
        uni.setStorageSync('baseUserInfo', baseUserInfo)
        uni.setStorageSync('deliveryFee', deliveryFee)
        uni.setStorageSync('shopInfo', shopInfo)

        await this.mergeGuestCart()
        uni.showToast({ title: '登录成功', icon: 'success' })
        setTimeout(() => {
          uni.redirectTo({ url: this.redirect })
        }, 350)
      } catch (error) {
        const message = error && (error.msg || (error.data && error.data.msg))
        uni.showToast({ title: message || '登录失败，请检查账号密码', icon: 'none' })
      } finally {
        this.submitting = false
      }
    },
  },
}
</script>

<style scoped>
.login-page {
  display: block;
  box-sizing: border-box;
  min-height: 100vh;
  padding: 42px 18px;
  background:
    radial-gradient(circle at 80% 10%, rgba(255, 194, 0, 0.28), transparent 34%),
    linear-gradient(160deg, #fff9e9 0%, #f3f5f8 52%, #eef1f5 100%);
}

.login-shell {
  display: block;
  position: relative;
  box-sizing: border-box;
  width: 100%;
  max-width: 460px;
  margin: 0 auto;
  padding-top: 18px;
}

.back-button {
  position: absolute;
  top: 0;
  left: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.86);
  color: #333;
  font-size: 32px;
  line-height: 36px;
  box-shadow: 0 6px 18px rgba(30, 35, 48, 0.1);
}

.brand-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  margin: 20px auto 18px;
  border-radius: 22px;
  background: linear-gradient(145deg, #ffd633, #ffb800);
  color: #653f00;
  font-size: 36px;
  font-weight: 700;
  box-shadow: 0 12px 28px rgba(255, 184, 0, 0.28);
}

.title {
  display: block;
  color: #22252a;
  font-size: 28px;
  font-weight: 700;
  line-height: 38px;
  text-align: center;
}

.subtitle {
  display: block;
  margin-top: 8px;
  color: #7b7f87;
  font-size: 14px;
  line-height: 22px;
  text-align: center;
}

.form-card {
  display: block;
  box-sizing: border-box;
  margin-top: 30px;
  padding: 24px;
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 18px 48px rgba(30, 35, 48, 0.11);
}

.field-label {
  display: block;
  margin-bottom: 8px;
  color: #454850;
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
}

.password-label {
  margin-top: 18px;
}

.field-input {
  display: block !important;
  box-sizing: border-box;
  width: 100%;
  height: 48px;
  padding: 0 14px;
  border: 1px solid #e4e6ea;
  border-radius: 12px;
  background: #f8f9fb;
  color: #25272c;
  font-size: 16px;
  line-height: 48px;
}

.login-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 50px;
  margin-top: 26px;
  border: 0;
  border-radius: 25px;
  background: linear-gradient(135deg, #ffd42a, #ffb800);
  color: #302200;
  font-size: 17px;
  font-weight: 700;
  line-height: 50px;
  box-shadow: 0 10px 24px rgba(255, 184, 0, 0.24);
}

.login-button[disabled] {
  opacity: 0.65;
}

.demo-account {
  display: block;
  margin-top: 20px;
  padding: 13px 15px;
  border-radius: 12px;
  background: #fff8dc;
  color: #755700;
  font-size: 13px;
  line-height: 21px;
}

.demo-title {
  display: block;
  margin-bottom: 3px;
  font-weight: 700;
}

.security-tip {
  display: block;
  margin-top: 18px;
  color: #999da5;
  font-size: 12px;
  line-height: 20px;
  text-align: center;
}

@media (max-width: 420px) {
  .login-page {
  display: block;
    padding: 28px 14px;
  }

  .form-card {
  display: block;
    padding: 20px 18px;
  }
}

::v-deep .field-input .uni-input-wrapper,
::v-deep .field-input .uni-input-input {
  box-sizing: border-box;
  display: block;
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: #25272c;
  font: inherit;
}
</style>
<style>
/* H5 native input reset */
.login-page .field-input input,
.login-page .field-input .uni-input-input {
  box-sizing: border-box;
  display: block;
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: #25272c;
  font: inherit;
}
</style>