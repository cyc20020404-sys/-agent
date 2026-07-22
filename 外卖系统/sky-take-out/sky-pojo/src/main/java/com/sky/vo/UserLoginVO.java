package com.sky.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.math.BigDecimal;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserLoginVO implements Serializable {

    private Long id;
    private String openid;
    private String token;
    private String name;
    private String phone;
    private String avatar;

    private BigDecimal deliveryFee;
    private String shopName;
    private String shopAddress;
    private String description;
    private Long shopId;

}
