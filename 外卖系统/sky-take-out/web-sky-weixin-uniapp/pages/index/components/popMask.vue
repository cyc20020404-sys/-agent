<!--选择多规格弹层-->
<template>
  <view class="more_norm_pop">
    <view class="title">{{ moreNormDishdata.name }}</view>
    <scroll-view class="items_cont" scroll-y="true" scroll-top="0rpx">
      <view class="item_row" v-for="(obj, index) in moreNormdata" :key="index">
        <view class="flavor_name">{{ obj.name }}</view>
        <view class="flavor_item">
          <view
            :class="{
              item: true,
              act: flavorDataes.findIndex((it) => item === it) !== -1,
            }"
            v-for="(item, ind) in obj.value"
            :key="ind"
            @click="checkMoreNormPop(obj.value, item)"
          >
            {{ item }}
          </view>
        </view>
      </view>
    </scroll-view>
    <view class="but_item">
      <view class="price">
        <text class="ico">￥</text>
        {{ moreNormDishdata.price }}
      </view>
      <view class="active"
        ><view class="dish_card_add" @click="addShop(moreNormDishdata, '普通')"
          >加入购物车</view
        ></view
      >
    </view>
    <view class="close" @click="closeMoreNorm(moreNormDishdata)"
      ><image
        class="close_img"
        src="../../../static/but_close.png"
        mode=""
      ></image
    ></view>
  </view>
</template>
<script>
export default {
  // 获取父级传的数据
  props: {
    // 空页面提示
    moreNormDishdata: {
      type: Object,
      default: () => ({}),
    },
    moreNormdata: {
      type: Array,
      default: () => [],
    },
    flavorDataes: {
      type: Array,
      default: () => [],
    },
  },
  methods: {
    checkMoreNormPop(obj, item) {
      this.$emit("checkMoreNormPop", { obj: obj, item: item });
    },
    addShop(obj) {
      console.log(obj);
      this.$emit("addShop", obj);
    },
    closeMoreNorm(obj) {
      this.$emit("closeMoreNorm", obj);
    },
  },
};
</script>
<style lang="scss" scoped>
.more_norm_pop {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 560rpx;
  max-width: 90%;
  padding: 36rpx;
  background: #fff;
  border-radius: 20rpx;
  box-sizing: border-box;

  .title {
    font-size: 36rpx;
    font-weight: 600;
    color: #1A1A1A;
    line-height: 64rpx;
    text-align: center;
  }

  .items_cont {
    max-height: 50vh;
    overflow-y: auto;

    .item_row {
      .flavor_name {
        font-size: 26rpx;
        color: #5C5C5C;
        line-height: 36rpx;
        padding: 20rpx 0 8rpx 8rpx;
      }

      .flavor_item {
        display: flex;
        flex-wrap: wrap;
        gap: 12rpx;

        .item {
          border: 1rpx solid #FFC200;
          border-radius: 8rpx;
          padding: 0 20rpx;
          height: 52rpx;
          line-height: 52rpx;
          font-size: 24rpx;
          color: #1A1A1A;
        }

        .act {
          background: #FFC200;
          border-color: #FFC200;
          font-weight: 600;
        }
      }
    }
  }

  .but_item {
    display: flex;
    align-items: center;
    position: relative;
    margin-top: 28rpx;

    .price {
      font-size: 44rpx;
      font-weight: 600;
      color: #E94E3C;
      .ico { font-size: 26rpx; }
    }

    .active {
      position: absolute;
      right: 0;
      bottom: 0;

      .dish_card_add {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 176rpx;
        height: 56rpx;
        font-size: 26rpx;
        font-weight: 600;
        color: #1A1A1A;
        background: #FFC200;
        border-radius: 28rpx;
      }
    }
  }
}

.close {
  position: absolute;
  bottom: -150rpx;
  left: 50%;
  transform: translateX(-50%);

  .close_img {
    width: 72rpx;
    height: 72rpx;
  }
}

/* #ifdef H5 */
/* H5 specification dialog fixes */
.more_norm_pop {
  display: block !important;
  box-sizing: border-box;
  width: calc(100% - 32px) !important;
  max-width: 520px;
  max-height: 78vh;
  padding: 22px !important;
  overflow: visible;
  border-radius: 18px !important;
  background: #fff;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.24);
}

.more_norm_pop .title {
  display: block !important;
  padding: 0 42px 16px;
  overflow: hidden;
  color: #22252a;
  font-size: 20px !important;
  font-weight: 600;
  line-height: 28px !important;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.more_norm_pop .items_cont {
  display: block !important;
  box-sizing: border-box;
  width: 100%;
  max-height: 46vh !important;
  margin: 0 !important;
}

.more_norm_pop .item_row {
  display: block;
  margin-bottom: 14px;
}

.more_norm_pop .flavor_name {
  display: block;
  height: auto !important;
  padding: 0 0 8px !important;
  color: #666;
  font-size: 14px !important;
  line-height: 20px !important;
}

.more_norm_pop .flavor_item {
  display: flex !important;
  flex-wrap: wrap;
  gap: 9px;
}

.more_norm_pop .flavor_item .item {
  display: flex !important;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  min-width: 76px;
  height: 38px !important;
  margin: 0 !important;
  padding: 0 15px !important;
  border: 1px solid #e6e7ea !important;
  border-radius: 19px !important;
  background: #f7f8fa;
  color: #444;
  font-size: 14px;
  line-height: 36px !important;
}

.more_norm_pop .flavor_item .item.act {
  border-color: #ffc200 !important;
  background: #fff8dc !important;
  color: #7a5700;
  font-weight: 600;
}

.more_norm_pop .but_item {
  display: flex !important;
  align-items: center;
  justify-content: space-between;
  min-height: 48px;
  margin: 18px 0 0 !important;
  padding: 16px 0 0 !important;
  border-top: 1px solid #f0f1f3;
}

.more_norm_pop .but_item .price {
  font-size: 25px !important;
  line-height: 42px !important;
}

.more_norm_pop .but_item .price .ico {
  font-size: 15px !important;
}

.more_norm_pop .but_item .active {
  position: static !important;
  display: block !important;
}

.more_norm_pop .dish_card_add {
  display: flex !important;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  width: 144px !important;
  height: 44px !important;
  border-radius: 22px !important;
  background: #ffc200 !important;
  color: #24262b;
  font-size: 16px !important;
  line-height: 44px !important;
}

.close {
  position: absolute !important;
  bottom: -60px !important;
  left: 50% !important;
  transform: translateX(-50%);
}

.close .close_img {
  display: block;
  width: 42px !important;
  height: 42px !important;
}
/* #endif */
</style>