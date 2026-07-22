<!-- 收货地址管理 -->
<template>
  <view class="address-page">
    <view class="page-nav">
      <view class="nav-back" @click="goBack">‹</view>
      <text class="nav-title">地址管理</text>
      <view class="nav-space"></view>
    </view>

    <scroll-view class="address-content" scroll-y>
      <view v-if="loading" class="state-box">
        <view class="loading-dot"></view>
        <text>正在加载地址…</text>
      </view>

      <view v-else-if="addressList.length === 0" class="state-box empty-box">
        <view class="empty-pin">⌖</view>
        <text class="empty-title">还没有收货地址</text>
        <text class="empty-desc">新增地址后，下单时可以直接选择</text>
      </view>

      <view v-else class="address-list">
        <view v-if="canChoose" class="choose-tip">请选择本次订单的收货地址</view>
        <view v-for="item in addressList" :key="item.id" class="address-card"
          :class="{ default: item.isDefault === 1 }" @click="chooseAddress(item)">
          <view class="card-main">
            <view class="address-line">
              <text class="tag" :class="'tag-' + item.label">{{ getLabel(item.label) }}</text>
              <text class="address-text">{{ fullAddress(item) }}</text>
            </view>
            <view class="contact-line">
              <text class="contact-name">{{ item.consignee }} {{ sexText(item.sex) }}</text>
              <text class="contact-phone">{{ item.phone }}</text>
            </view>
          </view>
          <view class="edit-button" @click.stop="editAddress(item)">✎</view>
          <view v-if="canChoose" class="select-arrow">›</view>
          <view class="card-footer" @click.stop>
            <view class="default-button" :class="{ checked: item.isDefault === 1 }"
              @click="setDefault(item)">
              <view class="check-dot">✓</view>
              <text>{{ item.isDefault === 1 ? "默认地址" : "设为默认" }}</text>
            </view>
            <text v-if="item.isDefault === 1" class="default-hint">下单时优先使用</text>
          </view>
        </view>
      </view>
    </scroll-view>

    <view class="bottom-action">
      <view class="add-button" @click="addAddress"><text class="plus">＋</text>新增收货地址</view>
    </view>
  </view>
</template>

<script>
import { queryAddressBookList, putAddressBookDefault } from "../api/api.js"
import { mapState, mapMutations } from "vuex"

export default {
  data () {
    return { loading: true, settingDefaultId: null, addressList: [] }
  },
  computed: {
    ...mapState(["addressBackUrl"]),
    canChoose () { return this.addressBackUrl === "/pages/order/index" },
  },
  onShow () { this.getAddressList() },
  methods: {
    ...mapMutations(["setAddress"]),
    goBack () {
      if (this.addressBackUrl) {
        uni.redirectTo({ url: this.addressBackUrl })
        return
      }
      uni.navigateBack({ delta: 1, fail: () => uni.switchTab({ url: "/pages/index/index" }) })
    },
    getAddressList () {
      this.loading = true
      queryAddressBookList().then((res) => {
        if (res.code !== 1) {
          uni.showToast({ title: res.msg || "地址加载失败", icon: "none" })
          return
        }
        this.addressList = Array.isArray(res.data) ? res.data : []
      }).catch(() => uni.showToast({ title: "地址加载失败，请稍后重试", icon: "none" }))
        .finally(() => { this.loading = false })
    },
    getLabel (label) {
      const labels = { "1": "公司", "2": "家", "3": "学校" }
      return labels[String(label)] || "其他"
    },
    sexText (sex) { return String(sex) === "0" ? "先生" : "女士" },
    fullAddress (item) {
      return [item.provinceName, item.cityName, item.districtName, item.detail].filter(Boolean).join("")
    },
    addAddress () { uni.navigateTo({ url: "/pages/addOrEditAddress/addOrEditAddress" }) },
    editAddress (item) {
      uni.navigateTo({ url: "/pages/addOrEditAddress/addOrEditAddress?type=编辑&id=" + item.id })
    },
    chooseAddress (item) {
      if (!this.canChoose) {
        this.editAddress(item)
        return
      }
      this.setAddress(item)
      uni.redirectTo({ url: "/pages/order/index?address=" + encodeURIComponent(JSON.stringify(item)) })
    },
    setDefault (item) {
      if (item.isDefault === 1 || this.settingDefaultId) return
      this.settingDefaultId = item.id
      putAddressBookDefault({ id: item.id }).then((res) => {
        if (res.code !== 1) {
          uni.showToast({ title: res.msg || "设置失败", icon: "none" })
          return
        }
        this.addressList = this.addressList.map((address) => ({
          ...address,
          isDefault: address.id === item.id ? 1 : 0,
        }))
        uni.showToast({ title: "已设为默认地址", icon: "success" })
      }).catch(() => uni.showToast({ title: "设置失败，请稍后重试", icon: "none" }))
        .finally(() => { this.settingDefaultId = null })
    },
  },
}
</script>

<style lang="scss" scoped>
.address-page { display: block; width: 100%; max-width: 750px; min-height: 100vh; margin: 0 auto; background: #f5f6f8; color: #292929; box-sizing: border-box; }
.page-nav { height: 54px; padding-top: env(safe-area-inset-top); display: flex; align-items: center; justify-content: space-between; background: #333; color: #fff; box-sizing: content-box; }
.nav-back, .nav-space { width: 58px; height: 54px; display: flex; align-items: center; justify-content: center; }
.nav-back { font-family: Arial, sans-serif; font-size: 40px; font-weight: 300; cursor: pointer; }
.nav-title { font-size: 17px; font-weight: 600; }
.address-content { height: calc(100vh - 54px - env(safe-area-inset-top)); padding: 14px 14px 118px; box-sizing: border-box; }
.address-list { display: block; }
.choose-tip { margin: 0 4px 10px; padding: 9px 12px; border-radius: 10px; background: #fff7d9; color: #7b5b00; font-size: 13px; }
.address-card { position: relative; display: block; margin-bottom: 12px; padding: 18px 16px 0; background: #fff; border: 1px solid transparent; border-radius: 14px; box-shadow: 0 3px 14px rgba(28,31,35,.04); box-sizing: border-box; cursor: pointer; }
.address-card.default { border-color: #f6d765; }
.card-main { display: block; padding-right: 50px; }
.address-line { display: flex; align-items: flex-start; gap: 9px; }
.tag { flex: 0 0 auto; min-width: 38px; height: 23px; padding: 0 8px; display: flex; align-items: center; justify-content: center; border-radius: 6px; background: #e7f3ff; color: #2f76b7; font-size: 12px; box-sizing: border-box; }
.tag-1 { background: #e8f5ff; color: #2672ae; }
.tag-2 { background: #fff4cd; color: #8a6500; }
.tag-3 { background: #e9f8ee; color: #33824e; }
.address-text { flex: 1; min-width: 0; font-size: 16px; font-weight: 600; line-height: 24px; color: #252525; word-break: break-all; }
.contact-line { margin-top: 12px; display: flex; align-items: center; gap: 14px; color: #777; font-size: 14px; }
.contact-name { font-weight: 500; }
.contact-phone { color: #8c8c8c; }
.edit-button { position: absolute; top: 18px; right: 15px; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; border-radius: 50%; background: #f5f6f7; color: #777; font-size: 20px; cursor: pointer; }
.select-arrow { position: absolute; right: 17px; top: 66px; color: #bbb; font-size: 26px; }
.card-footer { height: 50px; margin-top: 16px; display: flex; align-items: center; justify-content: space-between; border-top: 1px solid #f0f1f2; }
.default-button { display: flex; align-items: center; gap: 7px; color: #777; font-size: 13px; cursor: pointer; }
.check-dot { width: 19px; height: 19px; display: flex; align-items: center; justify-content: center; border: 1.5px solid #c9cbd0; border-radius: 50%; box-sizing: border-box; color: transparent; font-size: 12px; }
.default-button.checked { color: #765700; font-weight: 600; }
.default-button.checked .check-dot { border-color: #ffc200; background: #ffc200; color: #4f3a00; }
.default-hint { color: #aaa; font-size: 12px; }
.state-box { height: 62vh; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #999; font-size: 14px; }
.empty-pin { width: 78px; height: 78px; margin-bottom: 18px; display: flex; align-items: center; justify-content: center; border-radius: 50%; background: #fff4ce; color: #f2b700; font-size: 45px; }
.empty-title { font-size: 17px; font-weight: 600; color: #555; }
.empty-desc { margin-top: 8px; color: #999; font-size: 13px; }
.loading-dot { width: 24px; height: 24px; margin-bottom: 12px; border: 3px solid #eee; border-top-color: #ffc200; border-radius: 50%; animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.bottom-action { position: fixed; z-index: 10; left: 50%; bottom: 0; width: 100%; max-width: 750px; padding: 12px 14px calc(12px + env(safe-area-inset-bottom)); transform: translateX(-50%); background: rgba(255,255,255,.97); border-top: 1px solid #eee; box-sizing: border-box; }
.add-button { width: 100%; height: 48px; display: flex; align-items: center; justify-content: center; border-radius: 12px; background: #ffc200; color: #2b2400; font-size: 16px; font-weight: 600; cursor: pointer; }
.plus { margin-right: 4px; font-size: 20px; }
::v-deep .uni-actionsheet { display: none !important; }
@media (min-width: 751px) { .address-page { box-shadow: 0 0 30px rgba(0,0,0,.08); } .address-content { padding-left: 20px; padding-right: 20px; } }
</style>
