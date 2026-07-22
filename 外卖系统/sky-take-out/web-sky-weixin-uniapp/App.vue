<script>
export default {
  onLaunch: function () {
    // #ifdef H5
    // H5桌面端适配：将根字体大小限制为模拟480px手机视口，解决rpx在宽屏上渲染过大的问题
    var setRootFontSize = function() {
      var MAX_WIDTH = 480
      var w = Math.min(document.documentElement.clientWidth, MAX_WIDTH)
      document.documentElement.style.fontSize = (w / 20) + 'px'
    }
    setRootFontSize()
    window.addEventListener('resize', setRootFontSize)
    // H5环境补丁：模拟缺失的微信API
    if (!window.wx) {
      window.wx = {
        getMenuButtonBoundingClientRect: function() {
          return { top: 0, height: 44, width: 87 }
        }
      }
    }
    if (typeof uni !== 'undefined' && !uni.getMenuButtonBoundingClientRect) {
      uni.getMenuButtonBoundingClientRect = function() {
        return { top: 0, height: 44, width: 87 }
      }
    }
    // 自动登录（同步）：确保页面getData()执行前token已就位
    try {
      var xhr = new XMLHttpRequest()
      xhr.open('POST', 'http://localhost:8080/user/user/login', false)
      xhr.setRequestHeader('Content-Type', 'application/json')
      xhr.send(JSON.stringify({ code: 'h5-dev-code-' + Date.now(), location: '116.481488,39.990464' }))
      if (xhr.status === 200) {
        var resp = JSON.parse(xhr.responseText)
        if (resp.code === 1 && resp.data) {
          var d = resp.data
          this.$store.commit('setToken', d.token)
          this.$store.commit('setDeliveryFee', d.deliveryFee)
          this.$store.commit('setShopInfo', {
            shopName: d.shopName, shopAddress: d.shopAddress,
            description: d.description, shopId: d.shopId
          })
          this.$store.commit('setBaseUserInfo', { nickName: 'H5用户', avatarUrl: '', gender: 0 })
        }
      }
    } catch (e) {
      console.log('H5 auto-login failed:', e)
    }
    // #endif
  },
  onShow: function () {
  },
  onHide: function () {
  }
}
</script>

<style>
/*每个页面公共css */
/* #ifndef APP-PLUS-NVUE */
/* uni.css - 通用组件、模板样式库，可以当作一套ui库应用 */
/* 	    @import './common/uni.css'; */

/* H5 兼容 pc 所需 */
/* #ifdef H5 */
@media screen and (min-width: 768px) {
  body {
    overflow-y: scroll;
  }

  /* H5桌面端：手机视口模拟，限制最大宽度 */
  body {
    display: flex;
    justify-content: center;
    background: #e8e8e8 !important;
  }

  uni-app {
    width: 100%;
    max-width: 480px;
    min-height: 100vh;
    overflow-x: hidden;
    box-shadow: 0 0 40px rgba(0,0,0,0.12);
    position: relative;
    background: #efeff4;
  }

  /* 图片自适应 — 防止H5桌面超大图 */
  image {
    max-width: 100%;
  }

  uni-page-body {
    overflow-x: hidden;
  }
}

/* 顶栏通栏样式 */
/* .uni-top-window {
		    left: 0;
		    right: 0;
		} */

uni-page-body {
  background-color: #f5f5f5 !important;
  min-height: 100% !important;
  height: auto !important;
}

.uni-top-window uni-tabbar .uni-tabbar {
  background-color: #fff !important;
}

/* H5 document reset */
html,
body,
#app,
uni-app,
uni-page,
uni-page-wrapper,
uni-page-body {
  box-sizing: border-box;
  width: 100%;
  min-height: 100%;
  margin: 0;
  padding: 0;
}

body {
  overflow: hidden;
  background: #edf0f4;
  color: #24262b;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

uni-page-body {
  overflow: hidden;
}
.uni-app--showleftwindow .hideOnPc {
  display: none !important;
}
/* #endif */

/* 以下样式用于 hello uni-app 演示所需 */
page {
  background-color: #efeff4;
  height: 100%;
  font-size: 28rpx;
  line-height: 1.8;
  /* overflow: hidden; */
}
.fix-pc-padding {
  padding: 0 100rpx;
}
.uni-header-logo {
  padding: 30rpx;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  margin-top: 10rpx;
}

.uni-header-image {
  width: 200rpx;
  height: 200rpx;
}

.uni-hello-text {
  color: #7a7e83;
}

.uni-hello-addfile {
  text-align: center;
  line-height: 300rpx;
  background: #fff;
  padding: 50rpx;
  margin-top: 20rpx;
  font-size: 38rpx;
  color: #808080;
}
/* #endif*/

/*checkbox 选项框大小  */
/* uni-checkbox .uni-checkbox-input {
		width: 30rpx !important;
		height: 30rpx !important;
	} */
/*checkbox选中后样式  */
/* uni-checkbox .uni-checkbox-input.uni-checkbox-input-checked {
		background: #3D7EFF;
		border-color:#3D7EFF;
	} */
/*checkbox选中后图标样式  */
/* uni-checkbox .uni-checkbox-input.uni-checkbox-input-checked::before {
		width: 20rpx;
		height: 20rpx;
		line-height: 20rpx;
		text-align: center;
		font-size: 18rpx;
		color: #fff;
		background: transparent;
		transform: translate(-70%, -50%) scale(1);
		-webkit-transform: translate(-70%, -50%) scale(1);
	} */
</style>
