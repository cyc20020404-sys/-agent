package com.sky.controller.user;

import com.sky.constant.JwtClaimsConstant;
import com.sky.dto.H5LoginDTO;
import com.sky.dto.UserLoginDTO;
import com.sky.entity.User;
import com.sky.mapper.UserMapper;
import com.sky.properties.JwtProperties;
import com.sky.properties.ShopProperties;
import com.sky.result.Result;
import com.sky.service.UserService;
import com.sky.utils.JwtUtil;
import com.sky.utils.PasswordUtil;
import com.sky.vo.UserLoginVO;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/user/user")
@Api(tags = "C端用户相关接口")
@Slf4j
public class UserController {

    @Autowired
    private UserService userService;
    @Autowired
    private UserMapper userMapper;
    @Autowired
    private JwtProperties jwtProperties;

    @Autowired
    private ShopProperties shopProperties;

    /**
     * 微信登录
     *
     * @param userLoginDTO
     * @return
     */
    @PostMapping("/login")
    @ApiOperation("微信登录")
    public Result<UserLoginVO> login(@RequestBody UserLoginDTO userLoginDTO) {
        log.info("微信用户登录：{}", userLoginDTO.getCode());

        //微信登录
        User user = userService.wxLogin(userLoginDTO);

        //为微信用户生成jwt令牌
        Map<String, Object> claims = new HashMap<>();
        claims.put(JwtClaimsConstant.USER_ID, user.getId());
        String token = JwtUtil.createJWT(jwtProperties.getUserSecretKey(), jwtProperties.getUserTtl(), claims);

        UserLoginVO userLoginVO = UserLoginVO.builder()
                .id(user.getId())
                .openid(user.getOpenid())
                .token(token)
                .name(user.getName())
                .phone(user.getPhone())
                .avatar(user.getAvatar())
                .deliveryFee(shopProperties.getDeliveryFee())
                .shopId(shopProperties.getShopId())
                .shopAddress(shopProperties.getShopAddress())
                .shopName(shopProperties.getShopName())
                .description(shopProperties.getDescription())
                .build();
        return Result.success(userLoginVO);
    }

    /**
     * H5 login with phone number and password.
     */
    @PostMapping("/h5Login")
    @ApiOperation("H5 phone and password login")
    public Result<UserLoginVO> h5Login(@RequestBody H5LoginDTO loginDTO) {
        if (loginDTO == null || loginDTO.getPhone() == null || loginDTO.getPassword() == null) {
            return Result.error("请输入手机号和密码");
        }

        String phone = loginDTO.getPhone().trim();
        if (!phone.matches("^1\\d{10}$")) {
            return Result.error("手机号格式不正确");
        }

        User user = userMapper.getByPhone(phone);
        if (user == null || !PasswordUtil.matches(loginDTO.getPassword(), user.getPassword())) {
            return Result.error("手机号或密码错误");
        }

        Map<String, Object> claims = new HashMap<>();
        claims.put(JwtClaimsConstant.USER_ID, user.getId());
        String token = JwtUtil.createJWT(jwtProperties.getUserSecretKey(), jwtProperties.getUserTtl(), claims);

        UserLoginVO userLoginVO = UserLoginVO.builder()
                .id(user.getId())
                .openid(user.getOpenid())
                .token(token)
                .name(user.getName())
                .phone(user.getPhone())
                .avatar(user.getAvatar())
                .deliveryFee(shopProperties.getDeliveryFee())
                .shopId(shopProperties.getShopId())
                .shopAddress(shopProperties.getShopAddress())
                .shopName(shopProperties.getShopName())
                .description(shopProperties.getDescription())
                .build();
        return Result.success(userLoginVO);
    }
}
