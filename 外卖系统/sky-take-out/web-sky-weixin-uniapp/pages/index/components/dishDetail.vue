<!--选择多规格弹层-->
<template>
  <!-- 餐品详情 -->
  <view class="dish_detail_pop" v-if="dishDetailes.type == 1">
    <image
      mode="aspectFill"
      class="div_big_image"
      :src="dishDetailes.image"
    ></image>
    <view class="title">{{ dishDetailes.name }}</view>
    <view class="desc">{{ dishDetailes.description }}</view>
    <view class="but_item">
      <view class="price">
        <text class="ico">￥</text>
        {{ dishDetailes.price.toFixed(2) }}
      </view>
      <view
        class="active"
        v-if="dishDetailes.flavors.length === 0 && dishDetailes.dishNumber > 0"
      >
        <image
          src="../../../static/btn_red.png"
          @click="redDishAction(dishDetailes, '普通')"
          class="dish_red"
          mode=""
        ></image>
        <text class="dish_number">{{ dishDetailes.dishNumber }}</text>
        <image
          src="../../../static/btn_add.png"
          class="dish_add"
          @click="addDishAction(dishDetailes, '普通')"
          mode=""
        ></image>
      </view>

      <view class="active" v-if="dishDetailes.flavors.length > 0"
        ><view class="dish_card_add" @click="moreNormDataesHandle(dishDetailes)"
          >选择规格</view
        ></view
      >
      <view
        class="active"
        v-if="
          dishDetailes.dishNumber === 0 && dishDetailes.flavors.length === 0
        "
      >
        <view class="dish_card_add" @click="addDishAction(dishDetailes, '普通')"
          >加入购物车</view
        >
      </view>
    </view>
    <view class="close" @click="dishClose"
      ><image
        class="close_img"
        src="../../../static/but_close.png"
        mode=""
      ></image
    ></view>
  </view>
  <!-- end -->
  <!-- 套餐详情 -->
  <view class="dish_detail_pop" v-else>
    <scroll-view class="dish_items" scroll-y="true" scroll-top="0rpx">
      <view
        class="dish_item"
        v-for="(item, index) in dishMealData"
        :key="index"
      >
        <image class="div_big_image" :src="item.image" mode="aspectFill"></image>
        <view class="title">
          {{ item.name }}
          <text style="">X{{ item.copies }}</text>
        </view>
        <view class="desc">{{ item.description }}</view>
      </view>
    </scroll-view>
    <view class="but_item">
      <view class="price">
        <text class="ico">￥</text>
        {{ dishDetailes.price }}
      </view>
      <view
        class="active"
        v-if="dishDetailes.dishNumber && dishDetailes.dishNumber > 0"
      >
        <image
          src="../../../static/btn_red.png"
          @click="redDishAction(dishDetailes, '普通')"
          class="dish_red"
          mode=""
        ></image>
        <text class="dish_number">{{ dishDetailes.dishNumber }}</text>
        <image
          src="../../../static/btn_add.png"
          class="dish_add"
          @click="addDishAction(dishDetailes, '普通')"
          mode=""
        ></image>
      </view>
      <view class="active" v-else-if="dishDetailes.dishNumber == 0"
        ><view
          class="dish_card_add"
          @click="addDishAction(dishDetailes, '普通')"
          >加入购物车</view
        ></view
      >
    </view>
    <view class="close" @click="dishClose"
      ><image
        class="close_img"
        src="../../../static/but_close.png"
        mode=""
      ></image
    ></view>
  </view>
  <!-- end -->
</template>
<script>
export default {
  // 获取父级传的数据
  props: {
    dishDetailes: {
      type: Object,
      default: () => ({}),
    },
    openDetailPop: {
      type: Boolean,
      default: false,
    },
    dishMealData: {
      type: Array,
      default: () => [],
    },
  },
  methods: {
    // 加入购物车
    addDishAction(obj, item) {
      console.log(obj, item);
      this.$emit("addDishAction", { obj: obj, item: item });
    },
    redDishAction(obj, item) {
      this.$emit("redDishAction", { obj: obj, item: item });
    },
    // 选择规格
    moreNormDataesHandle(obj) {
      this.$emit("moreNormDataesHandle", obj);
    },
    // 关闭菜单详情
    dishClose() {
      this.$emit("dishClose");
    },
  },
};
</script>
<style lang="scss" scoped>
.dish_detail_pop {
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

  .div_big_image {
    display: block;
    width: 100%;
    max-height: 300rpx;
    border-radius: 12rpx;
  }

  .title {
    font-size: 36rpx;
    font-weight: 600;
    color: #1A1A1A;
    line-height: 64rpx;
    text-align: center;
  }

  .desc {
    font-size: 24rpx;
    color: #999;
    text-align: center;
    line-height: 34rpx;
    margin-bottom: 8rpx;
  }

  .dish_items {
    max-height: 60vh;
    overflow-y: auto;
  }

  .but_item {
    display: flex;
    align-items: center;
    position: relative;
    margin-top: 20rpx;
    min-height: 64rpx;

    .price {
      font-size: 44rpx;
      font-weight: 600;
      color: #E94E3C;
      line-height: 64rpx;

      .ico { font-size: 26rpx; }
    }

    .active {
      position: absolute;
      right: 0;
      bottom: 0;
      display: flex;
      align-items: center;

      .dish_add,
      .dish_red {
        display: block;
        width: 64rpx;
        height: 64rpx;
      }

      .dish_number {
        padding: 0 8rpx;
        line-height: 64rpx;
        font-size: 28rpx;
        font-weight: 600;
        color: #1A1A1A;
      }

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