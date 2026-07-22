<!-- 新增/编辑收货地址 -->
<template>
  <view class="address-page">
    <view class="page-nav">
      <view class="nav-back" @click="goBack">‹</view>
      <text class="nav-title">{{ showDel ? "编辑收货地址" : "新增收货地址" }}</text>
      <view class="nav-space"></view>
    </view>

    <scroll-view class="page-content" scroll-y>
      <view class="form-card">
        <view class="form-row">
          <text class="form-label">联系人</text>
          <input v-model.trim="form.name" class="form-input" type="text" maxlength="12"
            placeholder="请填写收货人的姓名" placeholder-class="form-placeholder" />
        </view>
        <view class="form-row">
          <text class="form-label">性别</text>
          <view class="gender-options">
            <view v-for="item in items" :key="item.value" class="gender-option"
              :class="{ selected: form.sex === item.value }" @click="sexChangeHandle(item.value)">
              <view class="radio-dot"><view class="radio-core"></view></view>
              <text>{{ item.name }}</text>
            </view>
          </view>
        </view>
        <view class="form-row">
          <text class="form-label">手机号</text>
          <input v-model.trim="form.phone" class="form-input" type="number" maxlength="11"
            placeholder="请填写收货人手机号码" placeholder-class="form-placeholder" />
        </view>
        <view class="form-row picker-row" @click="openRegionPicker">
          <text class="form-label">所在地区</text>
          <text class="region-value" :class="{ empty: !address }">{{ address || "请选择省 / 市 / 区" }}</text>
          <text class="row-arrow">›</text>
        </view>
        <view class="detail-row">
          <text class="form-label">详细地址</text>
          <input v-model.trim="form.detail" class="detail-input" type="text" maxlength="200"
            placeholder="街道、楼牌号等，例如：凤凰大道 1 号" placeholder-class="form-placeholder" />
        </view>
      </view>

      <view class="form-card label-card">
        <text class="form-label">地址标签</text>
        <view class="label-options">
          <view v-for="item in options" :key="item.type" class="label-option"
            :class="{ selected: form.type === item.type }" @click="getTextOption(item)">{{ item.name }}</view>
        </view>
      </view>
      <view class="tip-card">
        <text class="tip-title">填写提示</text>
        <text class="tip-text">准确的收货地址能帮助骑手更快找到您。</text>
      </view>
    </scroll-view>

    <view class="bottom-actions">
      <view class="save-button" :class="{ disabled: saving }" @click="addAddressFun">{{ saving ? "保存中…" : "保存地址" }}</view>
      <view v-if="showDel" class="delete-button" :class="{ disabled: saving }" @click="deleteAddressFun">删除地址</view>
    </view>

    <view v-if="showRegionPicker" class="region-mask" @click="cancelRegionPicker">
      <view class="region-panel" @click.stop>
        <view class="region-header">
          <text class="region-action cancel" @click="cancelRegionPicker">取消</text>
          <text class="region-heading">选择所在地区</text>
          <text class="region-action confirm" @click="confirmRegionPicker">确定</text>
        </view>
        <view class="region-columns">
          <scroll-view class="region-column" scroll-y :scroll-into-view="'province-' + pickerValue[0]">
            <view v-for="(item, index) in provinceList" :id="'province-' + index" :key="item.value" class="region-item" :class="{ active: pickerValue[0] === index }" @click="selectProvince(index)">{{ item.label }}</view>
          </scroll-view>
          <scroll-view class="region-column" scroll-y :scroll-into-view="'city-' + pickerValue[1]">
            <view v-for="(item, index) in cityList" :id="'city-' + index" :key="item.value" class="region-item" :class="{ active: pickerValue[1] === index }" @click="selectCity(index)">{{ item.label }}</view>
          </scroll-view>
          <scroll-view class="region-column" scroll-y :scroll-into-view="'area-' + pickerValue[2]">
            <view v-for="(item, index) in areaList" :id="'area-' + index" :key="item.value" class="region-item" :class="{ active: pickerValue[2] === index }" @click="selectArea(index)">{{ item.label }}</view>
          </scroll-view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { addAddressBook, delAddressBook, queryAddressBookById, editAddressBook } from "../api/api.js"
import provinceData from "../common/simple-address/city-data/province.js"
import cityData from "../common/simple-address/city-data/city.js"
import areaData from "../common/simple-address/city-data/area.js"

export default {
  data () {
    return {
      showDel: false,
      saving: false,
      items: [{ value: "0", name: "先生" }, { value: "1", name: "女士" }],
      options: [{ name: "公司", type: 1 }, { name: "家", type: 2 }, { name: "学校", type: 3 }],
      region: [],
      address: "",
      showRegionPicker: false,
      pickerValue: [0, 0, 0],
      provinceList: provinceData,
      cityList: cityData[0] || [],
      areaList: (areaData[0] && areaData[0][0]) || [],
      delId: "",
      form: { name: "", phone: "", type: 2, sex: "0", provinceCode: "", cityCode: "", districtCode: "", detail: "" },
    }
  },
  onLoad (options) {
    if (options && options.type === "编辑" && options.id) {
      this.showDel = true
      this.delId = options.id
      this.loadAddress(options.id)
    }
  },
  methods: {
    goBack () {
      uni.navigateBack({ delta: 1, fail: () => uni.redirectTo({ url: "/pages/address/address" }) })
    },
    loadAddress (id) {
      uni.showLoading({ title: "加载中" })
      queryAddressBookById({ id }).then((res) => {
        if (res.code !== 1 || !res.data) {
          uni.showToast({ title: res.msg || "地址加载失败", icon: "none" })
          return
        }
        const data = res.data
        this.form = {
          id: data.id,
          provinceCode: data.provinceCode || "",
          cityCode: data.cityCode || "",
          districtCode: data.districtCode || "",
          phone: data.phone || "",
          name: data.consignee || "",
          sex: String(data.sex == null ? "0" : data.sex),
          type: Number(data.label) || 2,
          detail: data.detail || "",
        }
        this.region = [data.provinceName, data.cityName, data.districtName].filter(Boolean)
        this.address = this.region.join(" / ")
      }).catch(() => uni.showToast({ title: "地址加载失败，请稍后重试", icon: "none" }))
        .finally(() => uni.hideLoading())
    },
    openRegionPicker () {
      let provinceIndex = provinceData.findIndex((item) => item.value === this.form.provinceCode)
      if (provinceIndex < 0) provinceIndex = 0
      this.cityList = cityData[provinceIndex] || []
      let cityIndex = this.cityList.findIndex((item) => item.value === this.form.cityCode)
      if (cityIndex < 0) cityIndex = 0
      this.areaList = (areaData[provinceIndex] && areaData[provinceIndex][cityIndex]) || []
      let areaIndex = this.areaList.findIndex((item) => item.value === this.form.districtCode)
      if (areaIndex < 0) areaIndex = 0
      this.pickerValue = [provinceIndex, cityIndex, areaIndex]
      this.showRegionPicker = true
    },
    selectProvince (index) {
      this.pickerValue = [index, 0, 0]
      this.cityList = cityData[index] || []
      this.areaList = (areaData[index] && areaData[index][0]) || []
    },
    selectCity (index) {
      this.pickerValue = [this.pickerValue[0], index, 0]
      this.areaList = (areaData[this.pickerValue[0]] && areaData[this.pickerValue[0]][index]) || []
    },
    selectArea (index) {
      this.pickerValue = [this.pickerValue[0], this.pickerValue[1], index]
    },
    cancelRegionPicker () { this.showRegionPicker = false },
    confirmRegionPicker () {
      const province = this.provinceList[this.pickerValue[0]]
      const city = this.cityList[this.pickerValue[1]]
      const area = this.areaList[this.pickerValue[2]]
      if (!province || !city || !area) return
      this.region = [province.label, city.label, area.label]
      this.address = this.region.join(" / ")
      this.form.provinceCode = province.value
      this.form.cityCode = city.value
      this.form.districtCode = area.value
      this.showRegionPicker = false
    },
    sexChangeHandle (value) { this.form.sex = value },
    getTextOption (item) { this.form.type = item.type },
    validate () {
      const name = (this.form.name || "").trim()
      const phone = (this.form.phone || "").trim()
      const detail = (this.form.detail || "").trim()
      if (!name) return "请填写联系人"
      if (!/^[\u0391-\uFFE5A-Za-z0-9·]{2,12}$/.test(name)) return "联系人请输入 2-12 个字符"
      if (!phone) return "请填写手机号"
      if (!/^1[3-9]\d{9}$/.test(phone)) return "请输入正确的 11 位手机号"
      if (this.region.length !== 3) return "请选择所在地区"
      if (!detail) return "请填写详细地址"
      if (detail.length < 2) return "详细地址请至少填写 2 个字符"
      return ""
    },
    addAddressFun () {
      if (this.saving) return
      const error = this.validate()
      if (error) {
        uni.showToast({ title: error, duration: 1800, icon: "none" })
        return
      }
      const params = {
        ...this.form,
        label: String(this.form.type),
        consignee: this.form.name.trim(),
        phone: this.form.phone.trim(),
        detail: this.form.detail.trim(),
        provinceName: this.region[0], cityName: this.region[1], districtName: this.region[2],
      }
      if (!this.showDel) delete params.id
      this.saving = true
      const request = this.showDel ? editAddressBook(params) : addAddressBook(params)
      request.then((res) => {
        if (res.code !== 1) {
          uni.showToast({ title: res.msg || "保存失败，请稍后重试", icon: "none" })
          return
        }
        uni.showToast({ title: "地址保存成功", icon: "success" })
        setTimeout(() => uni.redirectTo({ url: "/pages/address/address" }), 450)
      }).catch(() => uni.showToast({ title: "保存失败，请检查网络", icon: "none" }))
        .finally(() => { this.saving = false })
    },
    deleteAddressFun () {
      if (!this.delId || this.saving) return
      uni.showModal({
        title: "删除地址", content: "确定删除这个收货地址吗？", confirmColor: "#e5484d",
        success: (modal) => {
          if (!modal.confirm) return
          this.saving = true
          delAddressBook(this.delId).then((res) => {
            if (res.code !== 1) {
              uni.showToast({ title: res.msg || "删除失败", icon: "none" })
              return
            }
            uni.showToast({ title: "地址已删除", icon: "success" })
            setTimeout(() => uni.redirectTo({ url: "/pages/address/address" }), 350)
          }).catch(() => uni.showToast({ title: "删除失败，请稍后重试", icon: "none" }))
            .finally(() => { this.saving = false })
        },
      })
    },
  },
}
</script>

<style lang="scss" scoped>
.address-page { display: block; width: 100%; max-width: 750px; min-height: 100vh; margin: 0 auto; background: #f5f6f8; color: #272727; box-sizing: border-box; }
.page-nav { height: 54px; padding-top: env(safe-area-inset-top); display: flex; align-items: center; justify-content: space-between; background: #333; color: #fff; box-sizing: content-box; }
.nav-back, .nav-space { width: 58px; height: 54px; display: flex; align-items: center; justify-content: center; }
.nav-back { font-family: Arial, sans-serif; font-size: 40px; font-weight: 300; cursor: pointer; }
.nav-title { font-size: 17px; font-weight: 600; letter-spacing: .5px; }
.page-content { height: calc(100vh - 54px - env(safe-area-inset-top)); padding: 14px 14px 150px; box-sizing: border-box; }
.form-card, .tip-card { display: block; background: #fff; border-radius: 14px; box-shadow: 0 2px 14px rgba(28,31,35,.035); }
.form-row, .detail-row { min-height: 58px; margin: 0 16px; display: flex; align-items: center; border-bottom: 1px solid #f0f1f2; box-sizing: border-box; }
.form-row:last-child, .detail-row:last-child { border-bottom: 0; }
.form-label { width: 88px; flex: 0 0 88px; font-size: 15px; font-weight: 600; color: #333; }
.form-input { flex: 1; height: 58px; min-width: 0; padding: 0; font-size: 15px; color: #222; background: transparent; }
::v-deep .form-input .uni-input-input { width: 100%; height: 58px; padding: 0; border: 0; outline: 0; background: transparent; font-size: 15px; color: #222; box-sizing: border-box; }
.form-placeholder, .empty { color: #a7a9ad; }
.gender-options { flex: 1; display: flex; gap: 30px; }
.gender-option { display: flex; align-items: center; gap: 8px; font-size: 15px; color: #555; cursor: pointer; }
.radio-dot { width: 19px; height: 19px; border: 2px solid #c8cbd0; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-sizing: border-box; }
.gender-option.selected { color: #222; }
.gender-option.selected .radio-dot { border-color: #f3b900; }
.gender-option.selected .radio-core { width: 9px; height: 9px; border-radius: 50%; background: #ffc200; }
.picker-row { cursor: pointer; }
.region-value { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 15px; }
.row-arrow { margin-left: 10px; color: #aaa; font-size: 25px; }
.detail-row { min-height: 104px; align-items: flex-start; padding: 19px 0 16px; }
.detail-input { flex: 1; width: auto; min-height: 68px; padding: 0; font-size: 15px; line-height: 23px; color: #222; }
::v-deep .detail-input .uni-input-input { width: 100%; min-height: 68px; padding: 0; border: 0; outline: 0; background: transparent; font-size: 15px; line-height: 23px; color: #222; box-sizing: border-box; }
.label-card { min-height: 76px; margin-top: 12px; padding: 0 16px; display: flex; align-items: center; }
.label-options { display: flex; gap: 10px; flex-wrap: wrap; }
.label-option { min-width: 62px; height: 34px; padding: 0 14px; display: flex; align-items: center; justify-content: center; border: 1px solid #e5e6e8; border-radius: 18px; box-sizing: border-box; color: #666; font-size: 14px; cursor: pointer; }
.label-option.selected { color: #7a5900; border-color: #ffc200; background: #fff8dc; font-weight: 600; }
.tip-card { display: flex; margin-top: 12px; padding: 16px; display: flex; flex-direction: column; gap: 6px; }
.tip-title { font-size: 14px; font-weight: 600; color: #666; }
.tip-text { font-size: 13px; color: #999; }
.bottom-actions { position: fixed; z-index: 10; left: 50%; bottom: 0; width: 100%; max-width: 750px; padding: 12px 14px calc(12px + env(safe-area-inset-bottom)); transform: translateX(-50%); background: rgba(255,255,255,.97); border-top: 1px solid #eee; box-sizing: border-box; }
.save-button, .delete-button { display: flex; align-items: center; justify-content: center; width: 100%; height: 48px; line-height: 48px; margin: 0; padding: 0; border: 0; border-radius: 12px; font-size: 16px; font-weight: 600; }
.save-button { background: #ffc200; color: #2b2400; }
.save-button.disabled, .delete-button.disabled { opacity: .65; pointer-events: none; }
.delete-button { margin-top: 10px; background: #f4f4f5; color: #d83a40; }
::v-deep .uni-actionsheet { display: none !important; }
.region-mask { position: fixed; z-index: 50; inset: 0; display: flex; align-items: flex-end; justify-content: center; background: rgba(0,0,0,.42); }
.region-panel { width: 100%; max-width: 750px; background: #fff; border-radius: 18px 18px 0 0; padding-bottom: env(safe-area-inset-bottom); overflow: hidden; }
.region-header { height: 56px; padding: 0 18px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #eee; }
.region-heading { font-size: 16px; font-weight: 600; color: #333; }
.region-action { min-width: 48px; font-size: 15px; cursor: pointer; }
.region-action.cancel { color: #777; }
.region-action.confirm { color: #b27d00; font-weight: 600; text-align: right; }
.region-columns { height: 330px; display: flex; }
.region-column { width: 33.333%; height: 330px; border-right: 1px solid #f1f1f1; box-sizing: border-box; }
.region-column:last-child { border-right: 0; }
.region-item { min-height: 44px; padding: 11px 8px; display: flex; align-items: center; justify-content: center; box-sizing: border-box; color: #666; font-size: 14px; text-align: center; cursor: pointer; }
.region-item.active { background: #fff6d6; color: #775500; font-weight: 600; }
@media (min-width: 751px) { .address-page { box-shadow: 0 0 30px rgba(0,0,0,.08); } .page-content { padding-left: 20px; padding-right: 20px; } }
</style>
