<!-- 个人中心 -->
<template>
  <view class="profile-page">
    <view class="page-nav">
      <view class="nav-back" @click="goBack">‹</view>
      <text class="nav-title">个人中心</text>
      <view class="nav-space"></view>
    </view>

    <view class="page-content">
      <view class="profile-card">
        <view class="avatar-wrap">
          <image v-if="avatarUrl" class="avatar-image" :src="avatarUrl" mode="aspectFill"></image>
          <text v-else class="avatar-text">{{ avatarText }}</text>
        </view>
        <view class="profile-info">
          <view class="name-line">
            <text class="profile-name">{{ nickName }}</text>
            <text class="login-badge">已登录</text>
          </view>
          <text class="profile-phone">{{ maskedPhone }}</text>
          <text class="profile-tip">欢迎回来，今天也要好好吃饭</text>
        </view>
      </view>

      <view class="section-card service-card">
        <view class="section-heading">
          <text class="section-title">常用服务</text>
          <text class="section-subtitle">管理您的订单与配送信息</text>
        </view>
        <view class="service-grid">
          <view class="service-item" @click="goAddress">
            <view class="service-icon address-icon">⌖</view>
            <text class="service-name">地址管理</text>
            <text class="service-desc">维护收货地址</text>
          </view>
          <view class="service-item" @click="goOrder">
            <view class="service-icon order-icon">▤</view>
            <text class="service-name">历史订单</text>
            <text class="service-desc">查看全部订单</text>
          </view>
          <view class="service-item" @click="goChat">
            <view class="service-icon chat-icon">•••</view>
            <text class="service-name">在线客服</text>
            <text class="service-desc">问题在线咨询</text>
          </view>
        </view>
      </view>

      <view class="recent-section">
        <view class="recent-heading">
          <view>
            <text class="section-title">最近订单</text>
            <text v-if="recentOrdersList.length" class="order-total">共 {{ pageInfo.total }} 笔</text>
          </view>
          <text class="view-all" @click="goOrder">查看全部 ›</text>
        </view>

        <view v-if="loading && recentOrdersList.length === 0" class="state-card">
          <view class="loading-dot"></view>
          <text>订单加载中…</text>
        </view>

        <view v-else-if="recentOrdersList.length === 0" class="state-card empty-state">
          <view class="empty-icon">▤</view>
          <text class="empty-title">还没有订单</text>
          <text class="empty-desc">去首页选些喜欢的菜品吧</text>
        </view>

        <view v-else class="order-list">
          <view v-for="item in recentOrdersList" :key="item.id" class="order-card" @click="goDetail(item.id)">
            <view class="order-header">
              <view class="order-meta">
                <text class="shop-name">苍穹食堂</text>
                <text class="order-time">{{ item.orderTime }}</text>
              </view>
              <text class="status-badge" :class="'status-' + item.status">{{ getStatus(item) }}</text>
            </view>

            <view class="dish-row">
              <view class="dish-summary">
                <text class="dish-names">{{ dishNames(item.orderDetailList) }}</text>
                <text class="dish-count">共 {{ orderCount(item.orderDetailList) }} 件</text>
              </view>
              <view class="amount-wrap">
                <text class="amount-symbol">￥</text>
                <text class="order-amount">{{ Number(item.amount || 0).toFixed(2) }}</text>
              </view>
            </view>

            <view class="order-footer">
              <text class="order-number">订单号 {{ item.number || item.id }}</text>
              <view class="order-actions">
                <view class="action-button" @click.stop="oneOrderFun(item.id)">再来一单</view>
                <view v-if="item.status === 1 && getOvertime(item.orderTime) > 0"
                  class="action-button primary" @click.stop="goDetail(item.id)">去支付</view>
              </view>
            </view>
          </view>
        </view>

        <view v-if="loading && recentOrdersList.length" class="list-loading">{{ loadingText || "加载中…" }}</view>
        <view v-else-if="noMore && recentOrdersList.length" class="list-loading">已经到底了</view>
        <view v-if="!noMore && recentOrdersList.length" class="load-more" @click="loadMore">加载更多</view>
      </view>
    </view>
  </view>
</template>

<script>
import { getOrderPage, repetitionOrder, delShoppingCart } from "../api/api.js"
import { mapMutations } from "vuex"
import { statusWord, getOvertime } from "@/utils/index.js"

export default {
  data () {
    return {
      avatarUrl: "",
      nickName: "用户",
      phoneNumber: "",
      recentOrdersList: [],
      pageInfo: { page: 1, pageSize: 5, total: 0 },
      loadingText: "",
      loading: false,
    }
  },
  computed: {
    avatarText () {
      return (this.nickName || "用户").trim().slice(0, 1).toUpperCase()
    },
    maskedPhone () {
      const phone = String(this.phoneNumber || "")
      return /^1\d{10}$/.test(phone) ? phone.replace(/(\d{3})\d{4}(\d{4})/, "$1 **** $2") : (phone || "手机号未填写")
    },
    noMore () {
      return this.pageInfo.total > 0 && this.recentOrdersList.length >= this.pageInfo.total
    },
  },
  onShow () {
    this.loadProfile()
    this.pageInfo.page = 1
    this.recentOrdersList = []
    this.getList()
  },
  methods: {
    ...mapMutations(["setAddressBackUrl"]),
    loadProfile () {
      const user = this.$store.state.baseUserInfo || {}
      this.avatarUrl = user.avatarUrl || user.avatar || ""
      this.nickName = user.nickName || user.name || (user.phone ? "用户" + String(user.phone).slice(-4) : "苍穹用户")
      this.phoneNumber = user.phone || ""
    },
    getStatus (item) { return statusWord(item.status, item.orderTime) },
    getOvertime (time) { return getOvertime(time) },
    orderCount (list) {
      return (Array.isArray(list) ? list : []).reduce((sum, item) => sum + Number(item.number || 0), 0)
    },
    dishNames (list) {
      const names = (Array.isArray(list) ? list : []).map((item) => item.name).filter(Boolean)
      if (!names.length) return "订单菜品"
      return names.slice(0, 3).join("、") + (names.length > 3 ? " 等" : "")
    },
    getList () {
      if (this.loading) return
      this.loading = true
      this.loadingText = "订单加载中…"
      getOrderPage({ pageSize: this.pageInfo.pageSize, page: this.pageInfo.page }).then((res) => {
        if (res.code !== 1 || !res.data) {
          uni.showToast({ title: res.msg || "订单加载失败", icon: "none" })
          return
        }
        const records = Array.isArray(res.data.records) ? res.data.records : []
        this.recentOrdersList = this.pageInfo.page === 1 ? records : this.recentOrdersList.concat(records)
        this.pageInfo.total = Number(res.data.total || 0)
      }).catch(() => uni.showToast({ title: "订单加载失败，请稍后重试", icon: "none" }))
        .finally(() => {
          this.loading = false
          this.loadingText = ""
        })
    },
    loadMore () {
      if (this.loading || this.noMore) return
      this.pageInfo.page += 1
      this.getList()
    },
    goAddress () {
      this.setAddressBackUrl("/pages/my/my")
      uni.navigateTo({ url: "/pages/address/address?form=my" })
    },
    goOrder () { uni.navigateTo({ url: "/pages/historyOrder/historyOrder" }) },
    goChat () { uni.navigateTo({ url: "/pages/chat/chat" }) },
    goDetail (id) {
      this.setAddressBackUrl("/pages/my/my")
      uni.navigateTo({ url: "/pages/details/index?orderId=" + id })
    },
    async oneOrderFun (id) {
      if (this.loading) return
      uni.showLoading({ title: "正在加入购物车" })
      try {
        await delShoppingCart()
        const res = await repetitionOrder(id)
        if (res.code !== 1) {
          uni.showToast({ title: res.msg || "操作失败", icon: "none" })
          return
        }
        uni.showToast({ title: "已加入购物车", icon: "success" })
        setTimeout(() => uni.redirectTo({ url: "/pages/index/index" }), 350)
      } catch (error) {
        uni.showToast({ title: "操作失败，请稍后重试", icon: "none" })
      } finally {
        uni.hideLoading()
      }
    },
    goBack () { uni.redirectTo({ url: "/pages/index/index" }) },
  },
}
</script>

<style lang="scss" scoped>
.profile-page { display: block; width: 100%; max-width: 750px; min-height: 100vh; margin: 0 auto; background: #f4f5f7; color: #272727; box-sizing: border-box; }
.page-nav { position: sticky; z-index: 20; top: 0; height: 54px; padding-top: env(safe-area-inset-top); display: flex; align-items: center; justify-content: space-between; background: #333; color: #fff; box-sizing: content-box; }
.nav-back, .nav-space { width: 58px; height: 54px; display: flex; align-items: center; justify-content: center; }
.nav-back { font-family: Arial, sans-serif; font-size: 40px; font-weight: 300; cursor: pointer; }
.nav-title { font-size: 17px; font-weight: 600; }
.page-content { display: block; padding: 14px 14px 30px; }
.profile-card { min-height: 128px; padding: 22px 20px; display: flex; align-items: center; gap: 18px; border-radius: 18px; background: linear-gradient(135deg, #ffc200 0%, #ffd755 100%); box-shadow: 0 8px 25px rgba(214,159,0,.2); box-sizing: border-box; }
.avatar-wrap { width: 72px; height: 72px; flex: 0 0 72px; display: flex; align-items: center; justify-content: center; border: 4px solid rgba(255,255,255,.8); border-radius: 50%; background: #fff9df; color: #826000; overflow: hidden; box-sizing: border-box; }
.avatar-image { display: block; width: 100%; height: 100%; }
.avatar-text { font-size: 28px; font-weight: 700; }
.profile-info { min-width: 0; display: flex; flex-direction: column; gap: 7px; }
.name-line { display: flex; align-items: center; gap: 9px; }
.profile-name { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 21px; font-weight: 700; color: #2b2400; }
.login-badge { padding: 3px 8px; border-radius: 10px; background: rgba(255,255,255,.62); color: #725500; font-size: 11px; }
.profile-phone { font-size: 14px; color: rgba(50,39,0,.72); }
.profile-tip { font-size: 12px; color: rgba(50,39,0,.58); }
.section-card { display: block; margin-top: 14px; padding: 18px 16px; border-radius: 16px; background: #fff; box-shadow: 0 3px 15px rgba(25,29,34,.04); }
.section-heading { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 16px; }
.section-title { font-size: 17px; font-weight: 700; color: #303030; }
.section-subtitle { color: #aaa; font-size: 12px; }
.service-grid { display: flex; gap: 10px; }
.service-item { flex: 1; min-width: 0; padding: 15px 8px 13px; display: flex; flex-direction: column; align-items: center; border-radius: 13px; background: #f7f8fa; cursor: pointer; box-sizing: border-box; }
.service-item:active { background: #f0f1f3; }
.service-icon { width: 44px; height: 44px; margin-bottom: 10px; display: flex; align-items: center; justify-content: center; border-radius: 13px; font-family: Arial, sans-serif; font-size: 25px; font-weight: 700; box-sizing: border-box; }
.address-icon { background: #fff2c3; color: #a97b00; }
.order-icon { background: #e8f3ff; color: #3177b8; }
.chat-icon { background: #eaf8ef; color: #368454; font-size: 18px; letter-spacing: 1px; }
.service-name { font-size: 14px; font-weight: 600; color: #333; }
.service-desc { margin-top: 5px; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #aaa; font-size: 11px; }
.recent-section { display: block; margin-top: 20px; }
.recent-heading { margin: 0 3px 11px; display: flex; align-items: center; justify-content: space-between; }
.order-total { margin-left: 9px; color: #aaa; font-size: 12px; }
.view-all { color: #9a7410; font-size: 13px; cursor: pointer; }
.order-list { display: block; }
.order-card { display: block; margin-bottom: 12px; padding: 16px; border-radius: 16px; background: #fff; box-shadow: 0 3px 15px rgba(25,29,34,.04); cursor: pointer; }
.order-header { display: flex; align-items: flex-start; justify-content: space-between; padding-bottom: 13px; border-bottom: 1px solid #f0f1f2; }
.order-meta { min-width: 0; display: flex; flex-direction: column; gap: 5px; }
.shop-name { font-size: 15px; font-weight: 700; color: #333; }
.order-time { color: #aaa; font-size: 11px; }
.status-badge { flex: 0 0 auto; padding: 4px 9px; border-radius: 12px; background: #f1f2f3; color: #777; font-size: 12px; }
.status-1, .status-2 { background: #fff3c7; color: #8b6600; }
.status-3, .status-4 { background: #e8f3ff; color: #3379b7; }
.status-5 { background: #eaf8ef; color: #378152; }
.dish-row { padding: 15px 0; display: flex; align-items: center; justify-content: space-between; gap: 14px; }
.dish-summary { min-width: 0; display: flex; flex-direction: column; gap: 7px; }
.dish-names { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 15px; color: #3a3a3a; }
.dish-count { color: #aaa; font-size: 12px; }
.amount-wrap { flex: 0 0 auto; display: flex; align-items: baseline; color: #222; }
.amount-symbol { font-size: 12px; font-weight: 600; }
.order-amount { font-size: 18px; font-weight: 700; }
.order-footer { min-height: 38px; padding-top: 12px; display: flex; align-items: center; justify-content: space-between; gap: 12px; border-top: 1px solid #f0f1f2; }
.order-number { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #aaa; font-size: 11px; }
.order-actions { flex: 0 0 auto; display: flex; gap: 8px; }
.action-button { min-width: 74px; height: 32px; padding: 0 13px; display: flex; align-items: center; justify-content: center; border: 1px solid #ddd; border-radius: 17px; box-sizing: border-box; color: #555; font-size: 13px; cursor: pointer; }
.action-button.primary { border-color: #ffc200; background: #ffc200; color: #433200; font-weight: 600; }
.state-card { min-height: 210px; display: flex; flex-direction: column; align-items: center; justify-content: center; border-radius: 16px; background: #fff; color: #999; font-size: 13px; }
.loading-dot { width: 24px; height: 24px; margin-bottom: 12px; border: 3px solid #eee; border-top-color: #ffc200; border-radius: 50%; animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty-icon { width: 58px; height: 58px; margin-bottom: 13px; display: flex; align-items: center; justify-content: center; border-radius: 18px; background: #fff4ce; color: #b18200; font-size: 28px; }
.empty-title { color: #555; font-size: 15px; font-weight: 600; }
.empty-desc { margin-top: 7px; color: #aaa; font-size: 12px; }
.list-loading, .load-more { padding: 12px 0; text-align: center; color: #aaa; font-size: 12px; }
.load-more { color: #9a7410; cursor: pointer; }
::v-deep .uni-actionsheet { display: none !important; }
@media (min-width: 751px) { .profile-page { box-shadow: 0 0 30px rgba(0,0,0,.08); } .page-content { padding-left: 20px; padding-right: 20px; } }
</style>
