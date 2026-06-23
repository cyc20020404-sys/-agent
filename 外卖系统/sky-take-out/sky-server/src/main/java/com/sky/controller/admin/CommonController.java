package com.sky.controller.admin;

import com.sky.constant.MessageConstant;
import com.sky.properties.LocalOssProperties;
import com.sky.result.Result;
import com.sky.utils.UrlUtil;
import io.swagger.annotations.Api;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.UUID;


@RestController
@RequestMapping("/admin/common")
@Api(tags = "文件上传")
@Slf4j
public class CommonController {

    @Autowired
    private LocalOssProperties localOssProperties;

    @PostMapping("/upload")
    public Result<String> upload(MultipartFile file) {
        if (file.isEmpty()) {
            return Result.error("文件不能为空");
        }

        File dir = new File(localOssProperties.getUploadPath());
        if (!dir.exists() || !dir.isDirectory()) {
            boolean created = dir.mkdirs();
            if (created) {
                log.info("创建文件夹成功: {}", localOssProperties.getUploadPath());
            } else {
                log.warn("创建文件夹失败或已经存在: {}", localOssProperties.getUploadPath());
            }
        }

        String originalFilename = file.getOriginalFilename();
        if (originalFilename == null || originalFilename.isEmpty()) {
            return Result.error("文件名无效");
        }
        // 获取后缀
        String extension = originalFilename.substring(originalFilename.lastIndexOf("."));
        if (!extension.equalsIgnoreCase(".png") && !extension.equalsIgnoreCase(".jpg") && !extension.equalsIgnoreCase(".jpeg")) {
            return Result.error("文件格式不支持");
        }
        // 拼接新的随机名称
        originalFilename = UUID.randomUUID() + extension;


        // 确保文件路径安全，避免路径遍历攻击
        Path targetLocation = Paths.get(localOssProperties.getUploadPath()).resolve(originalFilename).normalize();
        try {
            Files.copy(file.getInputStream(), targetLocation, StandardCopyOption.REPLACE_EXISTING);
            log.info("文件上传成功: {}", originalFilename);
        } catch (IOException e) {
            log.error("文件上传失败: {}", originalFilename, e);
            return Result.error(MessageConstant.UPLOAD_FAILED);
        }

        // 你可以根据实际情况调整返回的文件访问链接
        String realFilePath = UrlUtil.buildImageUrl(originalFilename);
        return Result.success(realFilePath);
    }
}