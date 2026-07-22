-- Run after importing sky_take_out.sql.
ALTER TABLE `user`
    ADD COLUMN `password` varchar(120) DEFAULT NULL COMMENT 'H5 password hash' AFTER `phone`,
    ADD UNIQUE KEY `uk_user_phone` (`phone`);

INSERT INTO `user` (`openid`, `name`, `phone`, `password`, `sex`, `avatar`, `create_time`)
VALUES (NULL, 'H5测试用户', '13800138000', 'pbkdf2_sha256:120000:jmnNYhGNiCkrNu0yjZAOUw==:Q3b+Y08HCkkKGX/KtZiGJ2yXe3uI+FfDBqclfz850Cw=', '1', NULL, NOW());