<template>
  <view class="customer-box">
    <uni-nav-bar
      @clickLeft="goBack"
      left-icon="back"
      leftIcon="arrowleft"
      title="地址管理"
      statusBar="true"
      fixed="true"
      color="#ffffff"
      backgroundColor="#333333"
    ></uni-nav-bar>
    <view class="address">
      <view
        v-if="addressList && addressList.length > 0"
        class="address_content"
      >
        <view
          class="address_liests"
          v-for="(item, index) in addressList"
          :key="index"
        >
          <view class="list_item_top" @click.stop="choseAddress(index, item)">
            <view class="item_left">
              <view class="details">
                <text class="tag" :class="'tag' + item.label">{{
                  getLableVal(item.label)
                }}</text>
                <text class="address_word"
                  >{{ item.provinceName }}{{ item.cityName
                  }}{{ item.districtName }}{{ item.detail }}</text
                >
              </view>
              <view class="sale">
                <text class="name">{{
                  item.sex === "0"
                    ? item.consignee + " 先生"
                    : item.consignee + " 女士"
                }}</text>
                <text class="num">{{ item.phone }}</text>
              </view>
            </view>
            <view class="item_right">
              <image
                @click.stop="addOrEdit('编辑', item)"
                class="edit"
                src="../../static/edit.png"
              ></image>
            </view>
          </view>
          <view class="list_item_bottom">
            <label class="radio" @click.stop="getRadio(index, item)">
              <radio
                class="item_radio"
                v-if="testValue"
                color="#FFC200"
                :value="item.id"
                :checked="item.isDefault === 1 && isActive === index"
                @click.stop="getRadio(index, item)"
              />设为默认地址</label
            >
          </view>
        </view>
      </view>
      <empty
        v-if="isEmpty"
        boxHeight="100%"
        textLabel="一个地址都没有哦"
      ></empty>
      <view class="add_address">
        <button
          class="add_btn"
          type="primary"
          plain="true"
          @click="addOrEdit('新增')"
        >
          <text class="add-icon">+</text>
          新增收货地址
        </button>
      </view>
    </view>
  </view>
</template>

<script>
import { queryAddressBookList, putAddressBookDefault } from "../api/api.js";
import { mapState, mapMutations } from "vuex";
import uniNavBar from "@/components/uni-nav-bar/uni-nav-bar.vue";
import Empty from "@/components/empty/empty";
export default {
  components: { uniNavBar, Empty },
  data() {
    return {
      testValue: true,
      addressList: [],
      formRouter: "",
      isActive: null,
      isEmpty: false,
    };
  },
  onShow(options) {
    this.getAddressList();
    if (options && options.form) {
      this.formRouter = options.form;
    }
  },
  computed: {
    ...mapState(["addressBackUrl"]),
  },
  methods: {
    ...mapMutations(["setAddress"]),
    goBack() {
      uni.redirectTo({ url: this.addressBackUrl });
    },
    getLableVal(item) {
      switch (item) {
        case "1": return "公司";
        case "2": return "家";
        case "3": return "学校";
        default: return "其他";
      }
    },
    getAddressList() {
      this.testValue = false;
      uni.showLoading({ title: "加载中", mask: true });
      queryAddressBookList().then((res) => {
        if (res.code === 1) {
          setTimeout(() => { uni.hideLoading(); }, 100);
          this.testValue = true;
          this.addressList = res.data;
          this.isEmpty = true;
          this.addressList.map((val, index) => {
            if (val.isDefault === 1) this.isActive = index;
          });
        }
      });
    },
    addOrEdit(type, item) {
      if (type === "新增") {
        uni.redirectTo({ url: "/pages/addOrEditAddress/addOrEditAddress" });
      } else {
        uni.redirectTo({
          url: "/pages/addOrEditAddress/addOrEditAddress?type=编辑&id=" + item.id,
        });
      }
    },
    choseAddress(e, item) {
      if (this.addressBackUrl !== "/pages/order/index") return false;
      uni.redirectTo({ url: "/pages/order/index?address=" + JSON.stringify(item) });
      this.setAddress(item);
    },
    getRadio(index, item) {
      item.isDefault = 1;
      this.isActive = index;
      putAddressBookDefault({ id: item.id }).then((res) => {
        if (res.code === 1) {
          uni.showToast({ title: "默认地址设置成功", duration: 2000, icon: "none" });
        }
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.customer-box {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  padding-top: 80px;
  box-sizing: border-box;
}
.address {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  width: 100%;
  padding: 0 20rpx 120rpx;
  box-sizing: border-box;
  overflow-y: auto;

  .address_content {
    flex: 1;
    padding-bottom: 20rpx;

    .address_liests {
      width: 100%;
      background: #ffffff;
      border-radius: 12rpx;
      display: flex;
      flex-direction: column;
      margin-top: 20rpx;
      padding: 0 28rpx 0 12rpx;
      box-sizing: border-box;

      .list_item_top {
        flex: 1;
        width: 100%;
        display: flex;
        .item_left {
          flex: 1;
          overflow: hidden;
          margin-left: 12rpx;
          .details {
            margin-top: 42rpx;
            display: flex;
            height: 40rpx; line-height: 40rpx;
            .address_word {
              flex: 1;
              font-size: 28rpx; color: #333333;
              overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
            }
          }
          .sale {
            margin: 20rpx 0 16rpx;
            .name, .num {
              font-size: 28rpx; color: #999999;
              line-height: 40rpx;
            }
            .num { margin-left: 20rpx; }
          }
        }
        .item_right {
          width: 100rpx; text-align: right; padding-right: 18rpx;
          display: flex; align-items: center;
          .edit { width: 32rpx; height: 32rpx; padding: 24rpx; }
        }
      }
      .list_item_bottom {
        height: 80rpx; line-height: 80rpx;
        border-top: 1px solid #efefef;
        .radio {
          margin-left: 8rpx; font-size: 26rpx; color: #333333;
          .item_radio { transform: scale(0.7); }
        }
      }
    }
  }
  .add_address {
    position: fixed;
    bottom: 40rpx;
    left: 20rpx; right: 20rpx;
    margin: 0 auto;
    .add_btn {
      width: 100%; height: 86rpx; line-height: 86rpx;
      border-radius: 8rpx; background: #ffc200;
      border: 1px solid #ffc200;
      font-size: 30rpx; font-weight: 600; color: #333333;
      display: flex; align-items: center; justify-content: center;
      .add-icon { font-size: 32rpx; margin-right: 8rpx; margin-bottom: 4rpx; }
    }
  }
}
</style>