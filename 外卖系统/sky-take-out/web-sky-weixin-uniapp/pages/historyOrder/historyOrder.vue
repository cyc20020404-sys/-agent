<!-- 历史订单 -->
<template>
  <view class="history-page">
    <view class="page-nav">
      <view class="nav-back" @click="goBack">‹</view>
      <text class="nav-title">历史订单</text>
      <view class="nav-space"></view>
    </view>

    <view class="tab-bar">
      <view v-for="(tab, index) in tabs" :key="tab.label" class="tab-item"
        :class="{ active: tabIndex === index }" @click="changeTab(index)">
        <text>{{ tab.label }}</text>
        <view class="tab-line"></view>
      </view>
    </view>

    <view class="page-content">
      <view v-if="loading && orders.length === 0" class="state-card">
        <view class="loading-dot"></view>
        <text>订单加载中…</text>
      </view>

      <view v-else-if="orders.length === 0" class="state-card empty-state">
        <view class="empty-icon">▤</view>
        <text class="empty-title">{{ emptyTitle }}</text>
        <text class="empty-desc">{{ emptyDescription }}</text>
        <view class="home-button" @click="goHome">去首页看看</view>
      </view>

      <view v-else class="order-list">
        <view v-for="item in orders" :key="item.id" class="order-card" @click="goDetail(item.id)">
          <view class="order-header">
            <view class="order-meta">
              <text class="shop-name">苍穹食堂</text>
              <text class="order-time">{{ item.orderTime }}</text>
            </view>
            <text class="status-badge" :class="'status-' + item.status">{{ getStatus(item) }}</text>
          </view>

          <view class="dish-section">
            <view class="dish-summary">
              <text class="dish-names">{{ dishNames(item.orderDetailList) }}</text>
              <text class="dish-specs">{{ dishSpecs(item.orderDetailList) }}</text>
              <text class="dish-count">共 {{ orderCount(item.orderDetailList) }} 件商品</text>
            </view>
            <view class="amount-wrap">
              <text class="amount-label">实付</text>
              <text class="amount-symbol">￥</text>
              <text class="order-amount">{{ Number(item.amount || 0).toFixed(2) }}</text>
            </view>
          </view>

          <view class="order-footer">
            <view class="number-wrap">
              <text class="number-label">订单号</text>
              <text class="order-number">{{ item.number || item.id }}</text>
            </view>
            <view class="order-actions">
              <view class="action-button" @click.stop="oneMoreOrder(item.id)">再来一单</view>
              <view v-if="item.status === 1 && getOvertime(item.orderTime) > 0"
                class="action-button primary" @click.stop="goDetail(item.id)">去支付</view>
              <view v-if="item.status === 2" class="action-button primary"
                @click.stop="handleReminder(item.id)">催单</view>
            </view>
          </view>
        </view>
      </view>

      <view v-if="loading && orders.length" class="list-tip">加载中…</view>
      <view v-else-if="noMore && orders.length" class="list-tip">已经到底了</view>
      <view v-else-if="orders.length" class="load-more" @click="loadMore">加载更多</view>
    </view>

    <view v-if="showMessage" class="message-mask" @click="closeMessage">
      <view class="message-panel" @click.stop>
        <view class="message-icon">✓</view>
        <text class="message-title">催单成功</text>
        <text class="message-text">您的催单信息已发出，请耐心等待商家处理。</text>
        <view class="message-button" @click="closeMessage">知道了</view>
      </view>
    </view>
  </view>
</template>

<script>
import { getOrderPage, repetitionOrder, reminderOrder, delShoppingCart } from "../api/api.js"
import { mapMutations } from "vuex"
import { statusWord, getOvertime } from "@/utils/index.js"

export default {
  data () {
    return {
      tabs: [
        { label: "全部订单", status: "" },
        { label: "待付款", status: 1 },
        { label: "退款 / 取消", status: 6 },
      ],
      tabIndex: 0,
      orders: [],
      pageInfo: { page: 1, pageSize: 10, total: 0 },
      loading: false,
      actionLoading: false,
      showMessage: false,
    }
  },
  computed: {
    currentTab () { return this.tabs[this.tabIndex] },
    noMore () { return this.pageInfo.total > 0 && this.orders.length >= this.pageInfo.total },
    emptyTitle () {
      if (this.tabIndex === 1) return "没有待付款订单"
      if (this.tabIndex === 2) return "没有退款或取消订单"
      return "还没有历史订单"
    },
    emptyDescription () {
      return this.tabIndex === 0 ? "下单后可以在这里查看订单进度" : "当前分类暂时没有相关订单"
    },
  },
  onShow () { this.refreshList() },
  onPullDownRefresh () {
    this.refreshList().finally(() => uni.stopPullDownRefresh())
  },
  onReachBottom () { this.loadMore() },
  methods: {
    ...mapMutations(["setAddressBackUrl"]),
    refreshList () {
      this.pageInfo.page = 1
      this.pageInfo.total = 0
      this.orders = []
      return this.getList()
    },
    getList () {
      if (this.loading) return Promise.resolve()
      this.loading = true
      const params = { pageSize: this.pageInfo.pageSize, page: this.pageInfo.page }
      if (this.currentTab.status !== "") params.status = this.currentTab.status
      return getOrderPage(params).then((res) => {
        if (res.code !== 1 || !res.data) {
          uni.showToast({ title: res.msg || "订单加载失败", icon: "none" })
          return
        }
        const records = Array.isArray(res.data.records) ? res.data.records : []
        this.orders = this.pageInfo.page === 1 ? records : this.orders.concat(records)
        this.pageInfo.total = Number(res.data.total || 0)
      }).catch(() => uni.showToast({ title: "订单加载失败，请稍后重试", icon: "none" }))
        .finally(() => { this.loading = false })
    },
    changeTab (index) {
      if (this.tabIndex === index || this.loading) return
      this.tabIndex = index
      this.refreshList()
    },
    loadMore () {
      if (this.loading || this.noMore || !this.orders.length) return
      this.pageInfo.page += 1
      this.getList()
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
    dishSpecs (list) {
      const specs = (Array.isArray(list) ? list : []).map((item) => item.dishFlavor).filter(Boolean)
      return specs.slice(0, 2).join("、")
    },
    goDetail (id) {
      this.setAddressBackUrl("/pages/historyOrder/historyOrder")
      uni.navigateTo({ url: "/pages/details/index?orderId=" + id })
    },
    async oneMoreOrder (id) {
      if (this.actionLoading) return
      this.actionLoading = true
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
        this.actionLoading = false
        uni.hideLoading()
      }
    },
    handleReminder (id) {
      if (this.actionLoading) return
      this.actionLoading = true
      reminderOrder(id).then((res) => {
        if (res.code !== 1) {
          uni.showToast({ title: res.msg || "催单失败", icon: "none" })
          return
        }
        this.showMessage = true
      }).catch(() => uni.showToast({ title: "催单失败，请稍后重试", icon: "none" }))
        .finally(() => { this.actionLoading = false })
    },
    closeMessage () { this.showMessage = false },
    goBack () { uni.redirectTo({ url: "/pages/my/my" }) },
    goHome () { uni.redirectTo({ url: "/pages/index/index" }) },
  },
}
</script>

<style lang="scss" scoped>
.history-page { display: block; width: 100%; max-width: 750px; min-height: 100vh; margin: 0 auto; background: #f4f5f7; color: #292929; box-sizing: border-box; }
.page-nav { position: sticky; z-index: 20; top: 0; height: 54px; padding-top: env(safe-area-inset-top); display: flex; align-items: center; justify-content: space-between; background: #333; color: #fff; box-sizing: content-box; }
.nav-back, .nav-space { width: 58px; height: 54px; display: flex; align-items: center; justify-content: center; }
.nav-back { font-family: Arial, sans-serif; font-size: 40px; font-weight: 300; cursor: pointer; }
.nav-title { font-size: 17px; font-weight: 600; }
.tab-bar { position: sticky; z-index: 15; top: calc(54px + env(safe-area-inset-top)); height: 54px; padding: 0 8px; display: flex; align-items: stretch; background: #fff; box-shadow: 0 2px 10px rgba(20,24,29,.05); box-sizing: border-box; }
.tab-item { position: relative; flex: 1; display: flex; align-items: center; justify-content: center; color: #888; font-size: 14px; cursor: pointer; }
.tab-item.active { color: #2d2d2d; font-weight: 700; }
.tab-line { position: absolute; left: 50%; bottom: 0; width: 26px; height: 4px; transform: translateX(-50%); border-radius: 4px 4px 0 0; background: transparent; }
.tab-item.active .tab-line { background: #ffc200; }
.page-content { display: block; padding: 14px 14px 30px; }
.order-list { display: block; }
.order-card { display: block; margin-bottom: 12px; padding: 16px; border-radius: 16px; background: #fff; box-shadow: 0 3px 15px rgba(25,29,34,.045); cursor: pointer; }
.order-header { display: flex; align-items: flex-start; justify-content: space-between; padding-bottom: 13px; border-bottom: 1px solid #f0f1f2; }
.order-meta { min-width: 0; display: flex; flex-direction: column; gap: 5px; }
.shop-name { font-size: 15px; font-weight: 700; color: #333; }
.order-time { color: #aaa; font-size: 11px; }
.status-badge { flex: 0 0 auto; padding: 4px 9px; border-radius: 12px; background: #f1f2f3; color: #777; font-size: 12px; }
.status-1, .status-2 { background: #fff3c7; color: #8b6600; }
.status-3, .status-4 { background: #e8f3ff; color: #3379b7; }
.status-5 { background: #eaf8ef; color: #378152; }
.status-6 { background: #f3f3f4; color: #777; }
.dish-section { min-height: 92px; padding: 15px 0; display: flex; align-items: center; justify-content: space-between; gap: 16px; box-sizing: border-box; }
.dish-summary { min-width: 0; display: flex; flex-direction: column; gap: 6px; }
.dish-names { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 15px; color: #333; }
.dish-specs { min-height: 16px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #999; font-size: 12px; }
.dish-count { color: #aaa; font-size: 12px; }
.amount-wrap { flex: 0 0 auto; display: flex; align-items: baseline; }
.amount-label { margin-right: 5px; color: #999; font-size: 11px; }
.amount-symbol { font-size: 12px; font-weight: 600; }
.order-amount { font-size: 19px; font-weight: 700; }
.order-footer { min-height: 43px; padding-top: 12px; display: flex; align-items: center; justify-content: space-between; gap: 12px; border-top: 1px solid #f0f1f2; }
.number-wrap { min-width: 0; display: flex; align-items: center; gap: 5px; }
.number-label { flex: 0 0 auto; color: #bbb; font-size: 10px; }
.order-number { min-width: 0; max-width: 190px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #aaa; font-size: 10px; }
.order-actions { flex: 0 0 auto; display: flex; gap: 8px; }
.action-button { min-width: 72px; height: 32px; padding: 0 12px; display: flex; align-items: center; justify-content: center; border: 1px solid #ddd; border-radius: 17px; box-sizing: border-box; color: #555; font-size: 13px; cursor: pointer; }
.action-button.primary { border-color: #ffc200; background: #ffc200; color: #443300; font-weight: 600; }
.state-card { min-height: 58vh; display: flex; flex-direction: column; align-items: center; justify-content: center; border-radius: 16px; background: #fff; color: #999; font-size: 13px; }
.loading-dot { width: 25px; height: 25px; margin-bottom: 12px; border: 3px solid #eee; border-top-color: #ffc200; border-radius: 50%; animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty-icon { width: 66px; height: 66px; margin-bottom: 15px; display: flex; align-items: center; justify-content: center; border-radius: 20px; background: #fff4ce; color: #ac7e00; font-size: 31px; }
.empty-title { color: #555; font-size: 16px; font-weight: 600; }
.empty-desc { margin-top: 8px; color: #aaa; font-size: 12px; }
.home-button { height: 36px; margin-top: 20px; padding: 0 20px; display: flex; align-items: center; justify-content: center; border-radius: 19px; background: #ffc200; color: #453400; font-size: 13px; font-weight: 600; cursor: pointer; }
.list-tip, .load-more { padding: 13px 0; text-align: center; color: #aaa; font-size: 12px; }
.load-more { color: #92700e; cursor: pointer; }
.message-mask { position: fixed; z-index: 50; inset: 0; display: flex; align-items: center; justify-content: center; padding: 24px; background: rgba(0,0,0,.44); box-sizing: border-box; }
.message-panel { width: 100%; max-width: 330px; padding: 25px 22px 20px; display: flex; flex-direction: column; align-items: center; border-radius: 18px; background: #fff; box-sizing: border-box; }
.message-icon { width: 48px; height: 48px; margin-bottom: 13px; display: flex; align-items: center; justify-content: center; border-radius: 50%; background: #fff1b8; color: #8a6600; font-size: 25px; font-weight: 700; }
.message-title { font-size: 17px; font-weight: 700; color: #333; }
.message-text { margin-top: 9px; color: #888; font-size: 13px; line-height: 20px; text-align: center; }
.message-button { width: 100%; height: 42px; margin-top: 20px; display: flex; align-items: center; justify-content: center; border-radius: 11px; background: #ffc200; color: #443300; font-size: 14px; font-weight: 600; cursor: pointer; }
::v-deep .uni-actionsheet { display: none !important; }
@media (min-width: 751px) { .history-page { box-shadow: 0 0 30px rgba(0,0,0,.08); } .page-content { padding-left: 20px; padding-right: 20px; } }
</style>
