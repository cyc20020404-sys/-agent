<!--购物车弹层-->
<template>
  <view class="cart_pop" @click.stop="openOrderCartList = openOrderCartList">
    <view class="top_title">
      <view class="tit">购物车</view>
      <view class="clear" @click.stop="clearCardOrder()">
        <image
          class="clear_icon"
          src="../../../static/clear.png"
          mode=""
        ></image>
        <text class="clear-des">清空</text>
      </view>
    </view>
    <scroll-view class="card_order_list" scroll-y="true" scroll-top="40rpx">
      <view
        class="type_item_cont"
        v-for="(item, ind) in orderAndUserInfo"
        :key="ind"
      >
        <view
          class="type_item"
          v-for="(obj, index) in item.dishList"
          :key="index"
        >
          <view class="dish_img"
            ><image
              mode="aspectFill"
              :src="obj.image || '/static/imgDefault.png'"
              class="dish_img_url"
            ></image
          ></view>
          <view class="dish_info">
            <view class="dish_name">{{ obj.name }}</view>
            <view class="dish_dishFlavor" v-if="obj.dishFlavor">{{
              obj.dishFlavor
            }}</view>
            <view class="dish_price">
              <text class="ico">￥</text>
              {{ obj.amount }}
            </view>
            <view class="dish_active">
              <image
                v-if="obj.number && obj.number > 0"
                src="../../../static/btn_red.png"
                @click.stop="redDishAction(obj, '购物车')"
                class="dish_red"
                mode=""
              ></image>
              <text v-if="obj.number && obj.number > 0" class="dish_number">{{
                obj.number
              }}</text>
              <image
                src="../../../static/btn_add.png"
                class="dish_add"
                @click.stop="addDishAction(obj, '购物车')"
                mode=""
              ></image>
            </view>
          </view>
        </view>
      </view>
      <view class="seize_seat"></view>
    </scroll-view>
  </view>
</template>
<script>
export default {
  // 获取父级传的数据
  props: {
    orderAndUserInfo: {
      type: Array,
      default: () => [],
    },
    openOrderCartList: {
      type: Boolean,
      default: false,
    },
  },
  methods: {
    clearCardOrder() {
      this.$emit("clearCardOrder");
    },
    // 加入购物车
    addDishAction(obj, item) {
      this.$emit("addDishAction", obj, item);
    },
    redDishAction(obj, item) {
      this.$emit("redDishAction", obj, item);
    },
  },
};
</script>
<style lang="scss" scoped>
.cart_pop {
  width: 100%;
  position: absolute;
  bottom: 0;
  left: 0;
  height: 60vh;
  background-color: #fff;
  border-radius: 8rpx 8rpx 0 0;
  padding: 20rpx 30rpx 30rpx 30rpx;
  box-sizing: border-box;
  .top_title {
    display: flex;
    justify-content: space-between;
    border-bottom: solid 1px #ebeef5;
    padding-bottom: 20rpx;
    .tit {
      font-size: 40rpx;
      font-weight: bold;
      color: #20232a;
    }
    .clear {
      color: #999999;
      font-size: 28rpx;
      font-weight: 400;
      display: flex;
      align-items: center;
      font-family: PingFangSC, PingFangSC-Regular;

      // position: relative;
      // top: 14rpx;
      .clear_icon {
        // position: relative;
        // top: 0rpx;
        width: 30rpx;
        height: 30rpx;
        margin-right: 8rpx;
      }
      .clear-des {
        height: 56rpx;
        line-height: 56rpx;
      }
    }
  }
  .card_order_list {
    background-color: #fff;
    padding-top: 40rpx;
    box-sizing: border-box;
    height: calc(100% - 0rpx);
    flex: 1;
    position: relative;
    .type_item_cont {
      .user_info {
        display: flex;
        margin-bottom: 20rpx;
        .user_avatar {
          .user_avatar_icon {
            width: 42rpx;
            height: 42rpx;
            border-radius: 42rpx;
          }
          margin-right: 20rpx;
        }
        .user_name {
          color: #19232b;
          font-size: 24rpx;
        }
      }
    }

    .type_item {
      display: flex;
      margin-bottom: 40rpx;
      .dish_img {
        width: 128rpx;
        margin-right: 30rpx;
        .dish_img_url {
          display: block;
          width: 128rpx;
          height: 128rpx;
          border-radius: 8rpx;
        }
      }
      .dish_info {
        position: relative;
        flex: 1;
        padding-bottom: 120rpx;
        border-bottom: solid 1px #ebeef5;
        .dish_name {
          font-size: 32rpx;
          line-height: 40rpx;
          color: #333333;
          font-family: PingFangSC, PingFangSC-Semibold;
          font-weight: 600;
        }

        .dish_price {
          font-size: 32rpx;
          color: #e94e3c;
          position: absolute;
          bottom: 24rpx;
          .ico {
            font-size: 24rpx;
          }
        }
        .dish_active {
          position: absolute;
          right: 20rpx;
          bottom: 20rpx;
          display: flex;
          .dish_add,
          .dish_red {
            display: block;
            width: 72rpx;
            height: 72rpx;
          }
          .dish_number {
            padding: 0 10rpx;
            line-height: 72rpx;
            font-size: 30rpx;
            font-family: PingFangSC, PingFangSC-Medium;
            font-weight: 500;
          }
        }
      }
    }
    &::before {
      content: "";
      position: absolute;
      width: 100vw;
      height: 120rpx;
      z-index: 99;
      background: linear-gradient(
        0deg,
        rgba(255, 255, 255, 1) 10%,
        rgba(255, 255, 255, 0)
      );
      bottom: 0px;
      left: 0px;
    }
    .seize_seat {
      width: 100%;
      height: 120rpx;
    }
  }
  .dish_dishFlavor {
    position: absolute;
    left: 0;
    top: 40rpx;
  }
}

/* #ifdef H5 */
/* H5 shopping cart dialog fixes */
.cart_pop {
  position: absolute !important;
  bottom: 0;
  left: 0;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  width: 100%;
  height: min(62vh, 560px) !important;
  padding: 20px 18px 78px !important;
  overflow: hidden;
  border-radius: 20px 20px 0 0 !important;
  background: #fff;
  box-shadow: 0 -12px 34px rgba(0, 0, 0, 0.14);
}

.cart_pop .top_title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: none;
  padding: 0 0 14px !important;
  border-bottom: 1px solid #ebeef5;
}

.cart_pop .top_title .tit {
  color: #20232a;
  font-size: 20px !important;
  font-weight: 600;
  line-height: 28px;
}

.cart_pop .top_title .clear {
  display: flex;
  align-items: center;
  color: #8c9098;
  font-size: 14px !important;
}

.cart_pop .top_title .clear_icon {
  width: 16px !important;
  height: 16px !important;
  margin-right: 5px !important;
}

.cart_pop .top_title .clear-des {
  height: auto !important;
  line-height: 24px !important;
}

.cart_pop .card_order_list {
  min-height: 0;
  flex: 1;
  width: 100%;
  height: auto !important;
  padding: 8px 8px 72px 0 !important;
}

.cart_pop .type_item {
  display: flex !important;
  box-sizing: border-box;
  width: 100%;
  min-height: 108px;
  margin: 0 !important;
  padding: 14px 0 !important;
}

.cart_pop .dish_img {
  flex: 0 0 78px;
  width: 78px !important;
  margin-right: 12px !important;
}

.cart_pop .dish_img_url {
  display: block;
  width: 78px !important;
  height: 78px !important;
  border-radius: 10px !important;
  background: #f2f3f5;
}

.cart_pop .dish_info {
  position: relative;
  min-width: 0;
  flex: 1;
  padding: 0 0 36px !important;
  border-bottom: 1px solid #ebeef5;
}

.cart_pop .dish_name {
  overflow: hidden;
  color: #333;
  font-size: 16px !important;
  font-weight: 600;
  line-height: 22px !important;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cart_pop .dish_dishFlavor {
  position: static !important;
  display: block;
  margin-top: 4px;
  overflow: hidden;
  color: #8c9098;
  font-size: 12px;
  line-height: 18px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cart_pop .dish_price {
  position: absolute !important;
  bottom: 8px !important;
  left: 0;
  color: #e94e3c;
  font-size: 17px !important;
  line-height: 28px;
}

.cart_pop .dish_price .ico {
  font-size: 13px !important;
}

.cart_pop .dish_active {
  position: absolute !important;
  right: 32px !important;
  bottom: 9px !important;
  display: flex;
  align-items: center;
}

.cart_pop .dish_add,
.cart_pop .dish_red {
  display: block;
  width: 30px !important;
  height: 30px !important;
}

.cart_pop .dish_number {
  min-width: 30px;
  padding: 0 4px !important;
  font-size: 15px !important;
  line-height: 30px !important;
  text-align: center;
}

.cart_pop .card_order_list::before {
  display: none;
}

.cart_pop .seize_seat {
  width: 100%;
  height: 72px !important;
}
/* #endif */
</style>