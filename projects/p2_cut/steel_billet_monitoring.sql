/*
 Navicat Premium Dump SQL

 Source Server         : localhost
 Source Server Type    : MySQL
 Source Server Version : 80042 (8.0.42)
 Source Host           : localhost:3306
 Source Schema         : steelmaking_data

 Target Server Type    : MySQL
 Target Server Version : 80042 (8.0.42)
 File Encoding         : 65001

 Date: 29/09/2025 14:06:56
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for steel_billet_monitoring
-- ----------------------------
DROP TABLE IF EXISTS `steel_billet_monitoring`;
CREATE TABLE `steel_billet_monitoring`  (
  `billet_id` bigint NOT NULL AUTO_INCREMENT COMMENT '拟合钢坯编号',
  `strand_no` tinyint NOT NULL COMMENT '铸流编号',
  `cutting_time` datetime NOT NULL COMMENT '钢坯开始切割时间',
  `entry_time` datetime NOT NULL COMMENT '钢坯进入结晶器前12m时间',
  `exit_time` datetime NOT NULL COMMENT '钢坯离开结晶器前12m时间',
  `water_temperature` decimal(5, 2) NULL DEFAULT NULL COMMENT '二冷水平均水温',
  `water_pressure` decimal(6, 2) NULL DEFAULT NULL COMMENT '二冷水平均水压',
  `water_volume` decimal(8, 2) NULL DEFAULT NULL COMMENT '5段总水量',
  `water_pressure_sd` decimal(6, 2) NULL DEFAULT NULL COMMENT '二冷水水压标准差',
  `steel_temperature` decimal(7, 2) NULL DEFAULT NULL COMMENT '平均钢温',
  `drawing_speed` decimal(7, 2) NULL DEFAULT NULL COMMENT '平均拉速',
  `water_temperature_difference` decimal(7, 2) NULL DEFAULT NULL COMMENT '结晶器平均水温差',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
  PRIMARY KEY (`billet_id`) USING BTREE,
  INDEX `idx_cutting_time`(`cutting_time` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 13775 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '钢坯拟合数据表' ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
