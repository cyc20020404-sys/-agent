package com.sky.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ShopVO implements Serializable {

    private static final long serialVersionUID = 1L;

    //电话号码
    private String phone;

    //店铺名称
    private String shopName;

    //店铺地址
    private String shopAddress;

    //店铺ID
    private Long shopId;
}