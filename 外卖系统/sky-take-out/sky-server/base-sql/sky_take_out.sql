/*
 Navicat Premium Dump SQL

 Source Server         : 虚拟机1(104)
 Source Server Type    : MySQL
 Source Server Version : 80044 (8.0.44)
 Source Host           : 192.168.1.104:3306
 Source Schema         : sky_take_out

 Target Server Type    : MySQL
 Target Server Version : 80044 (8.0.44)
 File Encoding         : 65001

 Date: 28/12/2025 12:22:45
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for address_book
-- ----------------------------
DROP TABLE IF EXISTS `address_book`;
CREATE TABLE `address_book`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id` bigint NOT NULL COMMENT '用户id',
  `consignee` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '收货人',
  `sex` varchar(2) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '性别',
  `phone` varchar(11) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NOT NULL COMMENT '手机号',
  `province_code` varchar(12) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '省级区划编号',
  `province_name` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '省级名称',
  `city_code` varchar(12) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '市级区划编号',
  `city_name` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '市级名称',
  `district_code` varchar(12) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '区级区划编号',
  `district_name` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '区级名称',
  `detail` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '详细地址',
  `label` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '标签',
  `is_default` tinyint(1) NOT NULL DEFAULT 0 COMMENT '默认 0 否 1是',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 4 CHARACTER SET = utf8mb3 COLLATE = utf8mb3_bin COMMENT = '地址簿' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of address_book
-- ----------------------------
INSERT INTO `address_book` VALUES (2, 4, '小帅', '0', '18279383840', '36', '江西省', '3611', '上饶市', '361121', '上饶县', '香江明珠', '2', 0);
INSERT INTO `address_book` VALUES (3, 4, '大帅', '0', '18279383840', '44', '广东省', '4403', '深圳市', '440309', '龙华区', '共和花园', '2', 1);

-- ----------------------------
-- Table structure for category
-- ----------------------------
DROP TABLE IF EXISTS `category`;
CREATE TABLE `category`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `type` int NULL DEFAULT NULL COMMENT '类型   1 菜品分类 2 套餐分类',
  `name` varchar(32) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NOT NULL COMMENT '分类名称',
  `sort` int NOT NULL DEFAULT 0 COMMENT '顺序',
  `status` int NULL DEFAULT NULL COMMENT '分类状态 0:禁用，1:启用',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `create_user` bigint NULL DEFAULT NULL COMMENT '创建人',
  `update_user` bigint NULL DEFAULT NULL COMMENT '修改人',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `idx_category_name`(`name` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 44 CHARACTER SET = utf8mb3 COLLATE = utf8mb3_bin COMMENT = '菜品及套餐分类' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of category
-- ----------------------------
INSERT INTO `category` VALUES (11, 1, '酒水饮料', 30, 1, '2022-06-09 22:09:18', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (12, 1, '传统主食', 23, 1, '2022-06-09 22:09:32', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (13, 2, '人气套餐', 1, 1, '2022-06-09 22:11:38', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (15, 2, '商务套餐', 2, 1, '2022-06-09 22:14:10', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (16, 1, '蜀味烤鱼', 12, 1, '2022-06-09 22:15:37', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (17, 1, '蜀味牛蛙', 13, 1, '2022-06-09 22:16:14', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (18, 1, '特色蒸菜', 15, 1, '2022-06-09 22:17:42', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (19, 1, '新鲜时蔬', 16, 1, '2022-06-09 22:18:12', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (20, 1, '水煮鱼', 14, 1, '2022-06-09 22:22:29', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (21, 1, '汤类', 24, 1, '2022-06-10 10:51:47', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (23, 1, '新人特惠', 0, 1, '2025-10-22 20:07:22', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (24, 1, '热销', 0, 0, '2025-10-22 20:07:46', '2025-12-13 14:49:15', 1, 1);
INSERT INTO `category` VALUES (25, 1, '加料专区', 31, 1, '2025-10-22 20:11:44', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (27, 1, '粤式点心', 17, 1, '2025-12-05 22:18:57', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (28, 1, '湘菜系列', 18, 1, '2025-12-05 22:18:57', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (29, 1, '海鲜料理', 19, 1, '2025-12-05 22:18:57', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (30, 1, '烧烤系列', 20, 1, '2025-12-05 22:18:57', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (31, 1, '甜品小吃', 21, 1, '2025-12-05 22:18:57', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (32, 2, '工作午餐', 3, 1, '2025-12-05 22:18:57', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (33, 2, '周末特惠', 4, 1, '2025-12-05 22:18:57', '2025-12-05 22:29:14', 1, 1);
INSERT INTO `category` VALUES (34, 1, '火锅配菜', 22, 1, '2025-12-05 22:18:57', '2025-12-05 22:29:14', 1, 1);

-- ----------------------------
-- Table structure for dish
-- ----------------------------
DROP TABLE IF EXISTS `dish`;
CREATE TABLE `dish`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` varchar(32) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NOT NULL COMMENT '菜品名称',
  `category_id` bigint NOT NULL COMMENT '菜品分类id',
  `price` decimal(10, 2) NULL DEFAULT NULL COMMENT '菜品价格',
  `image` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '图片',
  `description` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '描述信息',
  `status` int NULL DEFAULT 1 COMMENT '0 停售 1 起售',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `create_user` bigint NULL DEFAULT NULL COMMENT '创建人',
  `update_user` bigint NULL DEFAULT NULL COMMENT '修改人',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `idx_dish_name`(`name` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 130 CHARACTER SET = utf8mb3 COLLATE = utf8mb3_bin COMMENT = '菜品' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of dish
-- ----------------------------
INSERT INTO `dish` VALUES (46, '王老吉', 11, 6.00, 'dc08b90a-4c8d-4b97-aad7-7daa36207b87.png', '', 1, '2022-06-09 22:40:47', '2022-06-09 22:40:47', 1, 1);
INSERT INTO `dish` VALUES (47, '北冰洋', 11, 8.00, '8e7f5c9d-3a8b-4f7e-9c8d-7b6a5d4c3b2a.png', '还是小时候的味道', 1, '2022-06-10 09:18:49', '2025-12-05 22:27:02', 1, 1);
INSERT INTO `dish` VALUES (48, '雪花啤酒', 11, 4.00, '7d6c5b4a-8f9e-4b8a-9d8c-8b7a6d5c4b3a.png', '雪花', 1, '2022-06-10 09:22:54', '2022-06-10 09:22:54', 1, 1);
INSERT INTO `dish` VALUES (49, '米饭', 12, 2.00, '6c5b4a3d-7e8f-4a9b-8c7d-9b8a7c6d5e4f.png', '精选五常大米', 1, '2022-06-10 09:30:17', '2022-06-10 09:30:17', 1, 1);
INSERT INTO `dish` VALUES (50, '馒头', 12, 6.00, '5b4a3d2c-6f7e-498b-7d6c-8a7b9d8c7e6f.png', '优质面粉', 1, '2022-06-10 09:34:28', '2025-12-05 22:27:02', 1, 1);
INSERT INTO `dish` VALUES (51, '老坛酸菜鱼', 20, 56.00, '4a3d2c1b-5e6f-487a-6c5d-9b8a7c6d5e4f.png', '原料：汤，草鱼，酸菜', 1, '2022-06-10 09:40:51', '2022-06-10 09:40:51', 1, 1);
INSERT INTO `dish` VALUES (52, '经典酸菜鮰鱼', 20, 66.00, '3d2c1b0a-4f5e-476b-5d4c-8a7b9d8c7e6f.png', '原料：酸菜，江团，鮰鱼', 1, '2022-06-10 09:46:02', '2022-06-10 09:46:02', 1, 1);
INSERT INTO `dish` VALUES (53, '蜀味水煮草鱼', 20, 38.00, '2c1b0a9d-3e4f-465a-4c3d-7b6a5d4c3b2a.png', '原料：草鱼，汤', 1, '2022-06-10 09:48:37', '2022-06-10 09:48:37', 1, 1);
INSERT INTO `dish` VALUES (54, '清炒小油菜', 19, 20.00, '1b0a9d8c-2f3e-454b-3b2c-6a5d4c3b2a1d.png', '原料：小油菜', 1, '2022-06-10 09:51:46', '2025-12-05 22:27:02', 1, 1);
INSERT INTO `dish` VALUES (55, '蒜蓉娃娃菜', 19, 18.00, '0a9d8c7b-1e2f-443a-2a1b-5d4c3b2a1d0c.png', '原料：蒜，娃娃菜', 1, '2022-06-10 09:53:37', '2022-06-10 09:53:37', 1, 1);
INSERT INTO `dish` VALUES (56, '清炒西兰花', 19, 22.00, '9d8c7b6a-0f1e-432b-190a-4c3b2a1d0c9b.png', '原料：西兰花', 1, '2022-06-10 09:55:44', '2025-12-05 22:27:02', 1, 1);
INSERT INTO `dish` VALUES (57, '炝炒圆白菜', 19, 18.00, '8c7b6a5d-9e0f-421a-089b-3b2a1d0c9b8a.png', '原料：圆白菜', 1, '2022-06-10 09:58:35', '2022-06-10 09:58:35', 1, 1);
INSERT INTO `dish` VALUES (58, '清蒸鲈鱼', 18, 98.00, '7b6a5d4c-8d9e-410b-978a-2a1d0c9b8a79.png', '原料：鲈鱼', 1, '2022-06-10 10:12:28', '2022-06-10 10:12:28', 1, 1);
INSERT INTO `dish` VALUES (59, '东坡肘子', 18, 138.00, '6a5d4c3b-7c8d-409a-867b-1d0c9b8a7968.png', '原料：猪肘棒', 1, '2022-06-10 10:24:03', '2022-06-10 10:24:03', 1, 1);
INSERT INTO `dish` VALUES (60, '梅菜扣肉', 18, 58.00, '5d4c3b2a-6b7c-398b-756a-0c9b8a796857.png', '原料：猪肉，梅菜', 1, '2022-06-10 10:26:03', '2022-06-10 10:26:03', 1, 1);
INSERT INTO `dish` VALUES (61, '剁椒鱼头', 18, 66.00, '4c3b2a1d-5a6b-387c-6459-9b8a79685746.png', '原料：鲢鱼，剁椒', 1, '2022-06-10 10:28:54', '2022-06-10 10:28:54', 1, 1);
INSERT INTO `dish` VALUES (62, '金汤酸菜牛蛙', 17, 88.00, '3b2a1d0c-495a-376d-5348-8a7968574635.png', '原料：鲜活牛蛙，酸菜', 1, '2022-06-10 10:33:05', '2022-06-10 10:33:05', 1, 1);
INSERT INTO `dish` VALUES (63, '香锅牛蛙', 17, 88.00, '2a1d0c9b-3849-367e-4237-796857463524.png', '配料：鲜活牛蛙，莲藕，青笋', 1, '2022-06-10 10:35:40', '2022-06-10 10:35:40', 1, 1);
INSERT INTO `dish` VALUES (64, '馋嘴牛蛙', 17, 88.00, '1d0c9b8a-2738-358f-3126-685746352413.png', '配料：鲜活牛蛙，丝瓜，黄豆芽', 1, '2022-06-10 10:37:52', '2022-06-10 10:37:52', 1, 1);
INSERT INTO `dish` VALUES (65, '草鱼2斤', 16, 68.00, '0c9b8a79-1627-349g-2015-574635241302.png', '原料：草鱼，黄豆芽，莲藕', 1, '2022-06-10 10:41:08', '2022-06-10 10:41:08', 1, 1);
INSERT INTO `dish` VALUES (66, '江团鱼2斤', 16, 110.00, '9b8a7968-0516-330h-1904-463524130291.png', '配料：江团鱼，黄豆芽，莲藕', 1, '2022-06-10 10:42:42', '2025-12-03 22:11:13', 1, 1);
INSERT INTO `dish` VALUES (67, '鮰鱼2斤', 16, 72.00, '8a796857-9405-321i-0893-352413029180.png', '原料：鮰鱼，黄豆芽，莲藕', 1, '2022-06-10 10:43:56', '2022-06-10 10:43:56', 1, 1);
INSERT INTO `dish` VALUES (68, '鸡蛋汤', 21, 4.00, 'a8306c72-8567-4855-8f02-46edab6d709d.png', '配料：鸡蛋，紫菜', 1, '2022-06-10 10:54:25', '2025-11-29 23:21:19', 1, 1);
INSERT INTO `dish` VALUES (69, '平菇豆腐汤', 21, 6.00, 'a43a418e-8315-45cd-bce4-9a3d62cd43a4.png', '配料：豆腐，平菇', 1, '2022-06-10 10:55:02', '2025-11-05 20:57:28', 1, 1);
INSERT INTO `dish` VALUES (72, '可口可乐', 11, 5.00, 'coke.png', '冰爽可口', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (73, '雪碧', 11, 5.00, 'sprite.png', '清爽柠檬味', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (74, '珍珠奶茶', 11, 15.00, 'bubble-tea.png', '珍珠Q弹，茶香浓郁', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (75, '鲜榨橙汁', 11, 12.00, 'orange-juice.png', '新鲜现榨，维生素C丰富', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (76, '拿铁咖啡', 11, 18.00, 'latte.png', '现磨咖啡，香浓顺滑', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (77, '柠檬红茶', 11, 10.00, 'lemon-tea.png', '柠檬清香，红茶醇厚', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (78, '百威啤酒', 11, 12.00, 'budweiser.png', '经典啤酒', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (79, '青岛啤酒', 11, 10.00, 'tsingtao.png', '清爽口感', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (80, '椰汁', 11, 8.00, 'coconut-juice.png', '天然椰汁', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (81, '冰糖雪梨', 11, 10.00, 'pear-juice.png', '润肺止咳', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (82, '牛肉面', 12, 25.00, 'beef-noodle.png', '大块牛肉，面条筋道', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (83, '炸酱面', 12, 18.00, 'zha-jiang-noodle.png', '老北京风味', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (84, '炒饭', 12, 20.00, 'fried-rice.png', '虾仁鸡蛋炒饭', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (85, '饺子(12个)', 12, 22.00, 'dumplings.png', '猪肉白菜馅', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (86, '馄饨', 12, 15.00, 'wonton.png', '鲜肉馄饨', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (87, '油条', 12, 3.00, 'youtiao.png', '香脆可口', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (88, '煎饼果子', 12, 12.00, 'jianbing.png', '天津风味', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (89, '虾饺皇', 27, 28.00, 'shrimp-dumpling.png', '晶莹剔透，虾肉饱满', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (90, '叉烧包', 27, 18.00, 'bbq-pork-bun.png', '松软香甜', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (91, '凤爪', 27, 25.00, 'chicken-feet.png', '豉汁蒸凤爪', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (92, '烧麦', 27, 22.00, 'shumai.png', '猪肉虾仁烧卖', 1, '2025-12-05 22:18:57', NULL, 1, NULL);
INSERT INTO `dish` VALUES (101, '毛血旺', 28, 68.00, 'maoxuewang.png', '麻辣鲜香，配料丰富', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (102, '小炒肉', 28, 38.00, 'stir-fry-pork.png', '农家小炒肉', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (103, '酸豆角炒肉末', 28, 28.00, 'sour-beans.png', '开胃下饭', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (104, '蒜蓉粉丝蒸扇贝', 29, 48.00, 'scallop.png', '6只装，蒜香浓郁', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (105, '白灼基围虾', 29, 58.00, 'shrimp.png', '鲜甜原味', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (106, '清蒸多宝鱼', 29, 98.00, 'turbot.png', '鱼肉鲜嫩', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (107, '椒盐皮皮虾', 29, 68.00, 'mantis-shrimp.png', '椒盐味，香脆可口', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (108, '羊肉串(5串)', 30, 25.00, 'lamb-skewer.png', '新疆风味', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (109, '烤鸡翅(2只)', 30, 18.00, 'chicken-wings.png', '蜜汁烤翅', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (110, '烤生蚝(4只)', 30, 38.00, 'oyster.png', '蒜蓉烤生蚝', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (111, '烤茄子', 30, 15.00, 'eggplant.png', '蒜蓉烤茄子', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (112, '烤玉米', 30, 10.00, 'corn.png', '香甜烤玉米', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (113, '芒果布丁', 31, 15.00, 'mango-pudding.png', '新鲜芒果制作', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (114, '红豆双皮奶', 31, 18.00, 'double-skin-milk.png', '顺德传统甜品', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (115, '炸鲜奶', 31, 22.00, 'fried-milk.png', '外酥里嫩', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (116, '桂花糕', 31, 16.00, 'osmanthus-cake.png', '桂花清香', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (117, '肥牛卷', 34, 32.00, 'beef-roll.png', '澳洲肥牛', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (118, '羊肉卷', 34, 30.00, 'lamb-roll.png', '内蒙古羊肉', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (119, '虾滑', 34, 35.00, 'shrimp-paste.png', '纯虾肉制作', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (120, '毛肚', 34, 38.00, 'tripe.png', '爽脆毛肚', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (121, '金针菇', 34, 12.00, 'enoki.png', '新鲜金针菇', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (122, '白菜', 34, 8.00, 'cabbage.png', '有机白菜', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (123, '土豆片', 34, 10.00, 'potato.png', '厚切土豆片', 1, '2025-12-05 22:27:02', NULL, 1, NULL);
INSERT INTO `dish` VALUES (128, '麻辣小龙虾', 23, 88.00, 'xiaolongxia.png', '秘制麻辣口味，鲜活小龙虾', 1, '2025-12-06 21:57:13', NULL, 1, NULL);
INSERT INTO `dish` VALUES (129, '冰镇酸梅汤', 11, 12.00, 'suanmeitang.png', '夏日解暑必备', 1, '2025-12-06 22:03:23', NULL, 1, NULL);

-- ----------------------------
-- Table structure for dish_flavor
-- ----------------------------
DROP TABLE IF EXISTS `dish_flavor`;
CREATE TABLE `dish_flavor`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `dish_id` bigint NOT NULL COMMENT '菜品',
  `name` varchar(32) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '口味名称',
  `value` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '口味数据list',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 153 CHARACTER SET = utf8mb3 COLLATE = utf8mb3_bin COMMENT = '菜品口味关系表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of dish_flavor
-- ----------------------------
INSERT INTO `dish_flavor` VALUES (40, 10, '甜味', '[\"无糖\",\"少糖\",\"半糖\",\"多糖\",\"全糖\"]');
INSERT INTO `dish_flavor` VALUES (41, 7, '忌口', '[\"不要葱\",\"不要蒜\",\"不要香菜\",\"不要辣\"]');
INSERT INTO `dish_flavor` VALUES (42, 7, '温度', '[\"热饮\",\"常温\",\"去冰\",\"少冰\",\"多冰\"]');
INSERT INTO `dish_flavor` VALUES (45, 6, '忌口', '[\"不要葱\",\"不要蒜\",\"不要香菜\",\"不要辣\"]');
INSERT INTO `dish_flavor` VALUES (46, 6, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (47, 5, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (48, 5, '甜味', '[\"无糖\",\"少糖\",\"半糖\",\"多糖\",\"全糖\"]');
INSERT INTO `dish_flavor` VALUES (49, 2, '甜味', '[\"无糖\",\"少糖\",\"半糖\",\"多糖\",\"全糖\"]');
INSERT INTO `dish_flavor` VALUES (50, 4, '甜味', '[\"无糖\",\"少糖\",\"半糖\",\"多糖\",\"全糖\"]');
INSERT INTO `dish_flavor` VALUES (51, 3, '甜味', '[\"无糖\",\"少糖\",\"半糖\",\"多糖\",\"全糖\"]');
INSERT INTO `dish_flavor` VALUES (52, 3, '忌口', '[\"不要葱\",\"不要蒜\",\"不要香菜\",\"不要辣\"]');
INSERT INTO `dish_flavor` VALUES (86, 52, '忌口', '[\"不要葱\",\"不要蒜\",\"不要香菜\",\"不要辣\"]');
INSERT INTO `dish_flavor` VALUES (87, 52, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (88, 51, '忌口', '[\"不要葱\",\"不要蒜\",\"不要香菜\",\"不要辣\"]');
INSERT INTO `dish_flavor` VALUES (89, 51, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (92, 53, '忌口', '[\"不要葱\",\"不要蒜\",\"不要香菜\",\"不要辣\"]');
INSERT INTO `dish_flavor` VALUES (93, 53, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (94, 54, '忌口', '[\"不要葱\",\"不要蒜\",\"不要香菜\"]');
INSERT INTO `dish_flavor` VALUES (95, 56, '忌口', '[\"不要葱\",\"不要蒜\",\"不要香菜\",\"不要辣\"]');
INSERT INTO `dish_flavor` VALUES (96, 57, '忌口', '[\"不要葱\",\"不要蒜\",\"不要香菜\",\"不要辣\"]');
INSERT INTO `dish_flavor` VALUES (97, 60, '忌口', '[\"不要葱\",\"不要蒜\",\"不要香菜\",\"不要辣\"]');
INSERT INTO `dish_flavor` VALUES (102, 67, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (103, 65, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (108, 66, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (109, 81, '甜度', '[\"无糖\",\"三分糖\",\"半糖\",\"七分糖\",\"全糖\"]');
INSERT INTO `dish_flavor` VALUES (110, 77, '甜度', '[\"无糖\",\"三分糖\",\"半糖\",\"七分糖\",\"全糖\"]');
INSERT INTO `dish_flavor` VALUES (111, 80, '甜度', '[\"无糖\",\"三分糖\",\"半糖\",\"七分糖\",\"全糖\"]');
INSERT INTO `dish_flavor` VALUES (112, 74, '甜度', '[\"无糖\",\"三分糖\",\"半糖\",\"七分糖\",\"全糖\"]');
INSERT INTO `dish_flavor` VALUES (113, 75, '甜度', '[\"无糖\",\"三分糖\",\"半糖\",\"七分糖\",\"全糖\"]');
INSERT INTO `dish_flavor` VALUES (116, 81, '温度', '[\"热\",\"常温\",\"去冰\",\"少冰\",\"正常冰\"]');
INSERT INTO `dish_flavor` VALUES (117, 72, '温度', '[\"热\",\"常温\",\"去冰\",\"少冰\",\"正常冰\"]');
INSERT INTO `dish_flavor` VALUES (118, 77, '温度', '[\"热\",\"常温\",\"去冰\",\"少冰\",\"正常冰\"]');
INSERT INTO `dish_flavor` VALUES (119, 80, '温度', '[\"热\",\"常温\",\"去冰\",\"少冰\",\"正常冰\"]');
INSERT INTO `dish_flavor` VALUES (120, 74, '温度', '[\"热\",\"常温\",\"去冰\",\"少冰\",\"正常冰\"]');
INSERT INTO `dish_flavor` VALUES (121, 73, '温度', '[\"热\",\"常温\",\"去冰\",\"少冰\",\"正常冰\"]');
INSERT INTO `dish_flavor` VALUES (122, 75, '温度', '[\"热\",\"常温\",\"去冰\",\"少冰\",\"正常冰\"]');
INSERT INTO `dish_flavor` VALUES (123, 76, '浓度', '[\"淡\",\"正常\",\"浓\"]');
INSERT INTO `dish_flavor` VALUES (124, 112, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (125, 110, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (126, 111, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (127, 109, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (128, 108, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (131, 109, '口味', '[\"原味\",\"孜然\",\"辣椒\",\"蜜汁\",\"蒜香\"]');
INSERT INTO `dish_flavor` VALUES (132, 108, '口味', '[\"原味\",\"孜然\",\"辣椒\",\"蜜汁\",\"蒜香\"]');
INSERT INTO `dish_flavor` VALUES (134, 117, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (135, 118, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (136, 119, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (137, 120, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (138, 121, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (139, 122, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (140, 123, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (141, 61, '辣度', '[\"微辣\",\"中辣\",\"特辣\"]');
INSERT INTO `dish_flavor` VALUES (142, 102, '辣度', '[\"微辣\",\"中辣\",\"特辣\"]');
INSERT INTO `dish_flavor` VALUES (143, 101, '辣度', '[\"微辣\",\"中辣\",\"特辣\"]');
INSERT INTO `dish_flavor` VALUES (144, 103, '辣度', '[\"微辣\",\"中辣\",\"特辣\"]');
INSERT INTO `dish_flavor` VALUES (148, 59, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (149, 60, '辣度', '[\"不辣\",\"微辣\",\"中辣\",\"重辣\"]');
INSERT INTO `dish_flavor` VALUES (151, 47, '甜度', '[\"少糖\",\"正常糖\",\"多糖\"]');
INSERT INTO `dish_flavor` VALUES (152, 46, '甜度', '[\"少糖\",\"正常糖\",\"多糖\"]');

-- ----------------------------
-- Table structure for employee
-- ----------------------------
DROP TABLE IF EXISTS `employee`;
CREATE TABLE `employee`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` varchar(32) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NOT NULL COMMENT '姓名',
  `username` varchar(32) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NOT NULL COMMENT '用户名',
  `password` varchar(64) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NOT NULL COMMENT '密码',
  `phone` varchar(11) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NOT NULL COMMENT '手机号',
  `sex` varchar(2) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NOT NULL COMMENT '性别',
  `id_number` varchar(18) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NOT NULL COMMENT '身份证号',
  `status` int NOT NULL DEFAULT 1 COMMENT '状态 0:禁用，1:启用',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `create_user` bigint NULL DEFAULT NULL COMMENT '创建人',
  `update_user` bigint NULL DEFAULT NULL COMMENT '修改人',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `idx_username`(`username` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 4 CHARACTER SET = utf8mb3 COLLATE = utf8mb3_bin COMMENT = '员工信息' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of employee
-- ----------------------------
INSERT INTO `employee` VALUES (1, '管理员', 'admin', 'e10adc3949ba59abbe56e057f20f883e', '13812312312', '1', '110101199001010047', 1, '2022-02-15 15:51:20', '2022-02-17 09:16:20', 1, 1);
INSERT INTO `employee` VALUES (3, '测试', 'test', 'e10adc3949ba59abbe56e057f20f883e', '18279383841', '0', '362111220009234011', 1, '2025-10-22 18:52:21', '2025-10-22 18:53:11', 1, 1);

-- ----------------------------
-- Table structure for order_detail
-- ----------------------------
DROP TABLE IF EXISTS `order_detail`;
CREATE TABLE `order_detail`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` varchar(32) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '名字',
  `image` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '图片',
  `order_id` bigint NOT NULL COMMENT '订单id',
  `dish_id` bigint NULL DEFAULT NULL COMMENT '菜品id',
  `setmeal_id` bigint NULL DEFAULT NULL COMMENT '套餐id',
  `dish_flavor` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '口味',
  `number` int NOT NULL DEFAULT 1 COMMENT '数量',
  `amount` decimal(10, 2) NOT NULL COMMENT '金额',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 26 CHARACTER SET = utf8mb3 COLLATE = utf8mb3_bin COMMENT = '订单明细表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of order_detail
-- ----------------------------

-- ----------------------------
-- Table structure for orders
-- ----------------------------
DROP TABLE IF EXISTS `orders`;
CREATE TABLE `orders`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `number` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '订单号',
  `status` int NOT NULL DEFAULT 1 COMMENT '订单状态 1待付款 2待接单 3已接单 4派送中 5已完成 6已取消 7退款',
  `user_id` bigint NOT NULL COMMENT '下单用户',
  `address_book_id` bigint NOT NULL COMMENT '地址id',
  `order_time` datetime NOT NULL COMMENT '下单时间',
  `checkout_time` datetime NULL DEFAULT NULL COMMENT '结账时间',
  `pay_method` int NOT NULL DEFAULT 1 COMMENT '支付方式 1微信,2支付宝',
  `pay_status` tinyint NOT NULL DEFAULT 0 COMMENT '支付状态 0未支付 1已支付 2退款',
  `amount` decimal(10, 2) NOT NULL COMMENT '实收金额',
  `remark` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '备注',
  `phone` varchar(11) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '手机号',
  `address` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '地址',
  `user_name` varchar(32) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '用户名称',
  `consignee` varchar(32) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '收货人',
  `cancel_reason` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '订单取消原因',
  `rejection_reason` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '订单拒绝原因',
  `cancel_time` datetime NULL DEFAULT NULL COMMENT '订单取消时间',
  `estimated_delivery_time` datetime NULL DEFAULT NULL COMMENT '预计送达时间',
  `delivery_status` tinyint(1) NOT NULL DEFAULT 1 COMMENT '配送状态  1立即送出  0选择具体时间',
  `delivery_time` datetime NULL DEFAULT NULL COMMENT '送达时间',
  `pack_amount` int NULL DEFAULT NULL COMMENT '打包费',
  `tableware_number` int NULL DEFAULT NULL COMMENT '餐具数量',
  `tableware_status` tinyint(1) NOT NULL DEFAULT 1 COMMENT '餐具数量状态  1按餐量提供  0选择具体数量',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 22 CHARACTER SET = utf8mb3 COLLATE = utf8mb3_bin COMMENT = '订单表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of orders
-- ----------------------------

-- ----------------------------
-- Table structure for setmeal
-- ----------------------------
DROP TABLE IF EXISTS `setmeal`;
CREATE TABLE `setmeal`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `category_id` bigint NOT NULL COMMENT '菜品分类id',
  `name` varchar(32) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NOT NULL COMMENT '套餐名称',
  `price` decimal(10, 2) NOT NULL COMMENT '套餐价格',
  `status` int NULL DEFAULT 1 COMMENT '售卖状态 0:停售 1:起售',
  `description` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '描述信息',
  `image` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '图片',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `create_user` bigint NULL DEFAULT NULL COMMENT '创建人',
  `update_user` bigint NULL DEFAULT NULL COMMENT '修改人',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `idx_setmeal_name`(`name` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 39 CHARACTER SET = utf8mb3 COLLATE = utf8mb3_bin COMMENT = '套餐' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of setmeal
-- ----------------------------
INSERT INTO `setmeal` VALUES (33, 13, '火锅双人餐', 168.00, 1, '包含锅底和丰富配菜', 'hotpot-set.png', '2025-12-05 22:27:02', '2025-12-05 23:27:03', 1, 1);
INSERT INTO `setmeal` VALUES (34, 15, '粤式早茶套餐', 128.00, 1, '经典广式点心组合', 'dimsum-set.png', '2025-12-05 22:27:02', '2025-12-05 23:27:13', 1, 1);
INSERT INTO `setmeal` VALUES (35, 13, '烧烤狂欢套餐', 158.00, 1, '多种烧烤组合', 'bbq-set.png', '2025-12-05 22:27:02', '2025-12-05 23:26:54', 1, 1);
INSERT INTO `setmeal` VALUES (36, 32, '工作日简餐A', 38.00, 1, '一荤一素一饭一汤', 'workday-a.png', '2025-12-05 22:27:02', '2025-12-05 23:26:20', 1, 1);
INSERT INTO `setmeal` VALUES (37, 32, '工作日简餐B', 48.00, 1, '两荤一素一饭一汤', 'workday-b.png', '2025-12-05 22:27:02', '2025-12-05 23:26:10', 1, 1);
INSERT INTO `setmeal` VALUES (38, 33, '周末家庭套餐', 258.00, 1, '适合4-5人家庭聚餐', 'weekend-family.png', '2025-12-05 22:27:02', '2025-12-05 23:26:33', 1, 1);

-- ----------------------------
-- Table structure for setmeal_dish
-- ----------------------------
DROP TABLE IF EXISTS `setmeal_dish`;
CREATE TABLE `setmeal_dish`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `setmeal_id` bigint NULL DEFAULT NULL COMMENT '套餐id',
  `dish_id` bigint NULL DEFAULT NULL COMMENT '菜品id',
  `name` varchar(32) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '菜品名称 （冗余字段）',
  `price` decimal(10, 2) NULL DEFAULT NULL COMMENT '菜品单价（冗余字段）',
  `copies` int NULL DEFAULT NULL COMMENT '菜品份数',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 127 CHARACTER SET = utf8mb3 COLLATE = utf8mb3_bin COMMENT = '套餐菜品关系' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of setmeal_dish
-- ----------------------------
INSERT INTO `setmeal_dish` VALUES (78, 37, 128, '麻辣小龙虾', 88.00, 1);
INSERT INTO `setmeal_dish` VALUES (79, 37, 64, '馋嘴牛蛙', 88.00, 1);
INSERT INTO `setmeal_dish` VALUES (80, 37, 57, '炝炒圆白菜', 18.00, 1);
INSERT INTO `setmeal_dish` VALUES (81, 37, 49, '米饭', 2.00, 1);
INSERT INTO `setmeal_dish` VALUES (82, 37, 68, '鸡蛋汤', 4.00, 1);
INSERT INTO `setmeal_dish` VALUES (83, 38, 106, '清蒸多宝鱼', 98.00, 1);
INSERT INTO `setmeal_dish` VALUES (84, 38, 58, '清蒸鲈鱼', 98.00, 1);
INSERT INTO `setmeal_dish` VALUES (85, 38, 128, '麻辣小龙虾', 88.00, 1);
INSERT INTO `setmeal_dish` VALUES (86, 38, 91, '凤爪', 25.00, 1);
INSERT INTO `setmeal_dish` VALUES (87, 38, 54, '清炒小油菜', 18.00, 1);
INSERT INTO `setmeal_dish` VALUES (88, 38, 49, '米饭', 2.00, 4);
INSERT INTO `setmeal_dish` VALUES (89, 38, 129, '冰镇酸梅汤', 12.00, 1);
INSERT INTO `setmeal_dish` VALUES (97, 37, 47, '北冰洋', 8.00, 1);
INSERT INTO `setmeal_dish` VALUES (98, 38, 48, '雪花啤酒', 4.00, 6);
INSERT INTO `setmeal_dish` VALUES (100, 35, 48, '雪花啤酒', 4.00, 2);
INSERT INTO `setmeal_dish` VALUES (101, 35, 111, '烤茄子', 15.00, 1);
INSERT INTO `setmeal_dish` VALUES (102, 35, 110, '烤生蚝(4只)', 38.00, 1);
INSERT INTO `setmeal_dish` VALUES (103, 35, 109, '烤鸡翅(2只)', 18.00, 1);
INSERT INTO `setmeal_dish` VALUES (104, 35, 108, '羊肉串(5串)', 25.00, 2);
INSERT INTO `setmeal_dish` VALUES (105, 34, 63, '香锅牛蛙', 88.00, 1);
INSERT INTO `setmeal_dish` VALUES (106, 34, 129, '冰镇酸梅汤', 12.00, 1);
INSERT INTO `setmeal_dish` VALUES (107, 34, 114, '红豆双皮奶', 18.00, 1);
INSERT INTO `setmeal_dish` VALUES (108, 34, 92, '烧麦', 22.00, 1);
INSERT INTO `setmeal_dish` VALUES (109, 34, 91, '凤爪', 25.00, 1);
INSERT INTO `setmeal_dish` VALUES (110, 34, 90, '叉烧包', 18.00, 1);
INSERT INTO `setmeal_dish` VALUES (111, 36, 89, '虾饺皇', 28.00, 1);
INSERT INTO `setmeal_dish` VALUES (112, 36, 46, '王老吉', 6.00, 1);
INSERT INTO `setmeal_dish` VALUES (113, 36, 68, '鸡蛋汤', 4.00, 1);
INSERT INTO `setmeal_dish` VALUES (114, 36, 49, '米饭', 2.00, 1);
INSERT INTO `setmeal_dish` VALUES (115, 36, 56, '清炒西兰花', 18.00, 1);
INSERT INTO `setmeal_dish` VALUES (116, 36, 102, '小炒肉', 38.00, 1);
INSERT INTO `setmeal_dish` VALUES (117, 34, 46, '王老吉', 6.00, 2);
INSERT INTO `setmeal_dish` VALUES (118, 33, 49, '米饭', 2.00, 2);
INSERT INTO `setmeal_dish` VALUES (119, 33, 123, '土豆片', 10.00, 1);
INSERT INTO `setmeal_dish` VALUES (120, 33, 122, '白菜', 8.00, 1);
INSERT INTO `setmeal_dish` VALUES (121, 33, 120, '毛肚', 38.00, 1);
INSERT INTO `setmeal_dish` VALUES (122, 33, 119, '虾滑', 35.00, 1);
INSERT INTO `setmeal_dish` VALUES (123, 33, 118, '羊肉卷', 30.00, 1);
INSERT INTO `setmeal_dish` VALUES (124, 33, 117, '肥牛卷', 32.00, 1);

-- ----------------------------
-- Table structure for shopping_cart
-- ----------------------------
DROP TABLE IF EXISTS `shopping_cart`;
CREATE TABLE `shopping_cart`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` varchar(32) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '商品名称',
  `image` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '图片',
  `user_id` bigint NOT NULL COMMENT '主键',
  `dish_id` bigint NULL DEFAULT NULL COMMENT '菜品id',
  `setmeal_id` bigint NULL DEFAULT NULL COMMENT '套餐id',
  `dish_flavor` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '口味',
  `number` int NOT NULL DEFAULT 1 COMMENT '数量',
  `amount` decimal(10, 2) NOT NULL COMMENT '金额',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 52 CHARACTER SET = utf8mb3 COLLATE = utf8mb3_bin COMMENT = '购物车' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of shopping_cart
-- ----------------------------

-- ----------------------------
-- Table structure for user
-- ----------------------------
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `openid` varchar(45) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '微信用户唯一标识',
  `name` varchar(32) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '姓名',
  `phone` varchar(11) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '手机号',
  `sex` varchar(2) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '性别',
  `id_number` varchar(18) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '身份证号',
  `avatar` varchar(500) CHARACTER SET utf8mb3 COLLATE utf8mb3_bin NULL DEFAULT NULL COMMENT '头像',
  `create_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 5 CHARACTER SET = utf8mb3 COLLATE = utf8mb3_bin COMMENT = '用户信息' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of user
-- ----------------------------
INSERT INTO `user` VALUES (4, 'osody1-4-rAldk_aeLWj9GOSCy4E', NULL, NULL, NULL, NULL, NULL, '2025-12-02 22:51:49');

SET FOREIGN_KEY_CHECKS = 1;
