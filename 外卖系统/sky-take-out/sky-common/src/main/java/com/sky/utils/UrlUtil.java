package com.sky.utils;

import lombok.extern.slf4j.Slf4j;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import javax.servlet.http.HttpServletRequest;


@Slf4j
public class UrlUtil {

    /**
     * 获取服务器基础URL
     *
     * @return 服务器基础URL，例如 http://localhost:8080
     */
    public static String getBaseUrl() {
        ServletRequestAttributes attributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        if (attributes == null) {
            return "http://localhost:8080";
        }

        HttpServletRequest request = attributes.getRequest();
        String scheme = request.getScheme(); // http
        String serverName = request.getServerName(); // localhost
        int serverPort = request.getServerPort(); // 8080

        StringBuilder baseUrl = new StringBuilder();
        baseUrl.append(scheme).append("://").append(serverName);
        if ((scheme.equals("http") && serverPort != 80) || (scheme.equals("https") && serverPort != 443)) {
            baseUrl.append(":").append(serverPort);
        }

        return baseUrl.toString();
    }

    /**
     * 拼接图片完整URL
     *
     * @param imagePath 图片路径
     * @return 完整的图片URL
     */
    public static String buildImageUrl(String imagePath) {
        if (imagePath == null || imagePath.isEmpty()) {
            return imagePath;
        }

        // 如果已经是完整的URL，则直接返回
        if (imagePath.startsWith("http://") || imagePath.startsWith("https://")) {
            return imagePath;
        }

        // 如果是相对路径，则拼接基础URL
        String baseUrl = getBaseUrl();
        if (imagePath.startsWith("/")) {
            return baseUrl + "/static" + imagePath;
        } else {
            return baseUrl + "/static/" + imagePath;
        }
    }

    public static String splitFileName(String allImagePath) {
        String[] split = allImagePath.split("/static/");
        return split[1];
    }
}