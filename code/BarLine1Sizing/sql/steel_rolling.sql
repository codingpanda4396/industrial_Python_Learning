CREATE DATABASE IF NOT EXISTS industrial_data;
USE industrial_data;

-- 创建数据点表
CREATE TABLE data_points (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip_address VARCHAR(20) NOT NULL COMMENT 'PLC网络地址',
    name VARCHAR(100) NOT NULL COMMENT '数据点名称',
    type VARCHAR(20) NOT NULL COMMENT '数据类型(bool/int/dint/real)',
    db_number INT NOT NULL COMMENT 'DB块号',
    start_offset INT NOT NULL COMMENT '起始偏移量',
    bit_offset INT NOT NULL COMMENT '位偏移量(仅bool类型有意义)',
    size INT NOT NULL COMMENT '数据大小(字节)',
    read_allow BOOLEAN NOT NULL COMMENT '是否允许读取',
    write_allow BOOLEAN NOT NULL COMMENT '是否允许写入',
    frequency INT NOT NULL COMMENT '采集频率(ms)',
    group_id INT NOT NULL COMMENT '组别',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据点配置表';

-- 创建实时数据表
CREATE TABLE realtime_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    point_id INT NOT NULL COMMENT '数据点ID',
    bool_value BOOLEAN NULL COMMENT '布尔值',
    int_value INT NULL COMMENT '整数值',
    real_value FLOAT NULL COMMENT '实数值',
    timestamp TIMESTAMP(3) NOT NULL COMMENT '数据时间戳(毫秒精度)',
    update_time TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '最后更新时间(毫秒精度)',
    FOREIGN KEY (point_id) REFERENCES data_points(id),
    INDEX (point_id, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实时数据表';

-- 创建历史数据表
CREATE TABLE historical_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    point_id INT NOT NULL COMMENT '数据点ID',
    bool_value BOOLEAN NULL COMMENT '布尔值',
    int_value INT NULL COMMENT '整数值',
    real_value FLOAT NULL COMMENT '实数值',
    timestamp TIMESTAMP(3) NOT NULL COMMENT '数据时间戳(毫秒精度)',
    create_time TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '数据创建时间(毫秒精度)',
    FOREIGN KEY (point_id) REFERENCES data_points(id),
    INDEX (point_id, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='历史数据表';

-- 插入数据点配置
INSERT INTO data_points (ip_address, name, type, db_number, start_offset, bit_offset, size, read_allow, write_allow, frequency, group_id) VALUES
('192.168.0.3', '看门狗', 'bool', 889, 0, 0, 1, TRUE, FALSE, 500, 1),
('192.168.0.3', '18#有钢信号', 'bool', 889, 0, 1, 1, TRUE, FALSE, 500, 1),
('192.168.0.3', '炉号', 'dint', 889, 4, 0, 4, TRUE, FALSE, 500, 1),
('192.168.0.3', '定尺', 'dint', 889, 8, 0, 4, TRUE, FALSE, 500, 1),
('192.168.0.3', '流号（末架）', 'int', 889, 36, 0, 2, TRUE, FALSE, 500, 1),
('192.168.0.3', '尾钢长度（热检）', 'int', 889, 38, 0, 2, TRUE, FALSE, 500, 1),
('192.168.0.3', '轧制规格', 'real', 889, 52, 0, 4, TRUE, FALSE, 500, 1),
('192.168.0.3', '尾钢长度（激光）', 'real', 889, 56, 0, 4, TRUE, FALSE, 500, 1),
('192.168.0.3', '轧前温度', 'real', 889, 60, 0, 4, TRUE, FALSE, 500, 1),
('192.168.0.3', '1流修正值', 'real', 889, 64, 0, 4, TRUE, FALSE, 500, 1),
('192.168.0.3', '2流修正值', 'real', 889, 68, 0, 4, TRUE, FALSE, 500, 1),
('192.168.0.3', '3流修正值', 'real', 889, 72, 0, 4, TRUE, FALSE, 500, 1),
('192.168.0.3', '4流修正值', 'real', 889, 76, 0, 4, TRUE, FALSE, 500, 1),
('192.168.0.3', '5流修正值', 'real', 889, 80, 0, 4, TRUE, FALSE, 500, 1),
('192.168.0.3', '6流修正值', 'real', 889, 84, 0, 4, TRUE, FALSE, 500, 1),
('192.168.0.3', '7流修正值', 'real', 889, 88, 0, 4, TRUE, FALSE, 500, 1),
('192.168.0.3', '8流修正值', 'real', 889, 92, 0, 4, TRUE, FALSE, 500, 1),
('192.168.0.3', '1流炼钢反馈重量', 'real', 889, 96, 0, 4, TRUE, FALSE, 500, 1),
('192.168.0.3', '2流炼钢反馈重量', 'real', 889, 100, 0, 4, TRUE, FALSE, 500, 1),
('192.168.0.3', '3流炼钢反馈重量', 'real', 889, 104, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '4流炼钢反馈重量', 'real', 889, 108, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '5流炼钢反馈重量', 'real', 889, 112, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '6流炼钢反馈重量', 'real', 889, 116, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '7流炼钢反馈重量', 'real', 889, 120, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '8流炼钢反馈重量', 'real', 889, 124, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '米重', 'real', 889, 128, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '尾钢设定', 'real', 889, 132, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '1#设定速度', 'real', 889, 136, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '2#设定速度', 'real', 889, 140, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '3#设定速度', 'real', 889, 144, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '4#设定速度', 'real', 889, 148, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '5#设定速度', 'real', 889, 152, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '6#设定速度', 'real', 889, 156, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '7#设定速度', 'real', 889, 160, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '8#设定速度', 'real', 889, 164, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '9#设定速度', 'real', 889, 168, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '10#设定速度', 'real', 889, 172, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '11#设定速度', 'real', 889, 176, 0, 4, TRUE, FALSE, 500, 2),
('192.168.0.3', '12#设定速度', 'real', 889, 180, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '13#设定速度', 'real', 889, 184, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '14#设定速度', 'real', 889, 188, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '15#设定速度', 'real', 889, 192, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '16#设定速度', 'real', 889, 196, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '17#设定速度', 'real', 889, 200, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '18#设定速度', 'real', 889, 204, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '1#辊径', 'real', 889, 208, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '2#辊径', 'real', 889, 212, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '3#辊径', 'real', 889, 216, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '4#辊径', 'real', 889, 220, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '5#辊径', 'real', 889, 224, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '6#辊径', 'real', 889, 228, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '7#辊径', 'real', 889, 232, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '8#辊径', 'real', 889, 236, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '9#辊径', 'real', 889, 240, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '10#辊径', 'real', 889, 244, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '11#辊径', 'real', 889, 248, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '12#辊径', 'real', 889, 252, 0, 4, TRUE, FALSE, 500, 3),
('192.168.0.3', '13#辊径', 'real', 889, 256, 0, 4, TRUE, FALSE, 500, 4),
('192.168.0.3', '14#辊径', 'real', 889, 260, 0, 4, TRUE, FALSE, 500, 4),
('192.168.0.3', '15#辊径', 'real', 889, 264, 0, 4, TRUE, FALSE, 500, 4),
('192.168.0.3', '16#辊径', 'real', 889, 268, 0, 4, TRUE, FALSE, 500, 4),
('192.168.0.3', '17#辊径', 'real', 889, 272, 0, 4, TRUE, FALSE, 500, 4),
('192.168.0.3', '18#辊径', 'real', 889, 276, 0, 4, TRUE, FALSE, 500, 4);

-- 批量初始化bool类型数据点
INSERT INTO realtime_data (point_id, bool_value, timestamp)
SELECT id, FALSE, NOW(3) FROM data_points WHERE type = 'bool';

-- 批量初始化int/dint类型数据点
INSERT INTO realtime_data (point_id, int_value, timestamp)
SELECT id, 0, NOW(3) FROM data_points WHERE type IN ('int', 'dint');

-- 批量初始化real类型数据点
INSERT INTO realtime_data (point_id, real_value, timestamp)
SELECT id, 0.0, NOW(3) FROM data_points WHERE type = 'real';