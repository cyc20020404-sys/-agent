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
</style>