<template>
  <view class="navBar">
    <!-- 背景图：底层 -->
    <image class="index_bg" src="../../../static/bg.png" mode="aspectFill"></image>
    <!-- 个人中心：底层左下角 -->
    <view @click="myCenterFun" class="person-box">
      <image class="test_image" src="../../../static/center.png"></image>
      <span class="person-title">个人中心</span>
    </view>
  </view>
</template>

<script>
export default {
  computed: {
    ht: function () {
      // #ifdef H5
      return 10
      // #endif
      // #ifndef H5
      try {
        let res = uni.getMenuButtonBoundingClientRect()
        return res.top + 5
      } catch (e) {
        return 44
      }
      // #endif
    },
  },
  methods: {
    myCenterFun () {
      uni.navigateTo({
        url: '/pages/my/my'
      })
    }
  }
}
</script>

<style src="./navbar.scss" lang="scss"></style>