package com.sky;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.core.env.Environment;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.transaction.annotation.EnableTransactionManagement;

@SpringBootApplication
@EnableTransactionManagement //开启注解方式的事务管理
@Slf4j
@EnableCaching//开发缓存注解功能
@EnableScheduling //开启任务调度
public class SkyApplication {
    public static void main(String[] args) {
        ConfigurableApplicationContext context = SpringApplication.run(SkyApplication.class, args);

        String profile = getEnviroment(context);
        System.out.println("current environment: " + profile);
        System.out.println("server start success......");
    }

    private static String getEnviroment(ConfigurableApplicationContext context) {
        Environment environment = context.getBean(Environment.class);
        String[] activeProfiles = environment.getActiveProfiles();
        return activeProfiles.length > 0 ? activeProfiles[0] : "default";
    }
}