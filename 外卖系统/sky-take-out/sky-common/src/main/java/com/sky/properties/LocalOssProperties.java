package com.sky.properties;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "sky.oss")
@Data
//本地图片存储配置
public class LocalOssProperties {

    private String uploadPath;
}
