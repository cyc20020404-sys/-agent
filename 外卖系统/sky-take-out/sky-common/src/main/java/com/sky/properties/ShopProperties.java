package com.sky.properties;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;

@Component
@ConfigurationProperties(prefix = "sky.shop")
@Data
public class ShopProperties {

    private BigDecimal deliveryFee;
    private String phone;
    private String shopName;
    private String shopAddress;
    private Long shopId;
    private String description;
}