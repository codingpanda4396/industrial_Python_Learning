-- 新建炼钢数据采集数据库
CREATE DATABASE IF NOT EXISTS steelmaking_data DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE steelmaking_data;

-- 创建炼钢数据点表
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
    UNIQUE KEY (ip_address, name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='炼钢数据点配置表';

-- 创建炼钢实时数据表
CREATE TABLE realtime_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    point_id INT NOT NULL UNIQUE COMMENT '数据点ID',
    bool_value BOOLEAN NULL COMMENT '布尔值',
    int_value INT NULL COMMENT '整数值',
    real_value FLOAT NULL COMMENT '实数值',
    timestamp TIMESTAMP(3) NOT NULL COMMENT '数据时间戳(毫秒精度)',
    update_time TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '最后更新时间(毫秒精度)',
    FOREIGN KEY (point_id) REFERENCES data_points(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='炼钢实时数据表';

-- 创建炼钢历史数据表
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='炼钢历史数据表';

-- 插入炼钢PLC 172.16.1.20的数据点配置
INSERT INTO data_points (ip_address, name, type, db_number, start_offset, bit_offset, size, read_allow, write_allow, frequency, group_id) VALUES
('172.16.1.20', '中间包连续测温温度', 'dint', 7, 4, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '中间包手动测温', 'dint', 4, 30, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '1流结晶器拉速', 'real', 6, 36, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '1流结晶器通钢量', 'real', 15, 0, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '2流结晶器拉速', 'real', 6, 40, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '2流结晶器通钢量', 'real', 15, 4, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '3流结晶器拉速', 'real', 6, 44, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '3流结晶器通钢量', 'real', 15, 8, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '4流结晶器拉速', 'real', 6, 48, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '4流结晶器通钢量', 'real', 15, 12, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '5流结晶器拉速', 'real', 6, 52, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '5流结晶器通钢量', 'real', 15, 16, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '6流结晶器拉速', 'real', 6, 56, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '6流结晶器通钢量', 'real', 15, 20, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '7流结晶器拉速', 'real', 6, 60, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '7流结晶器通钢量', 'real', 15, 24, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '8流结晶器拉速', 'real', 6, 64, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '8流结晶器通钢量', 'real', 15, 28, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '1流定尺', 'real', 6, 72, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.20', '2流定尺', 'real', 6, 76, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.20', '3流定尺', 'real', 6, 80, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.20', '4流定尺', 'real', 6, 84, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.20', '5流定尺', 'real', 6, 88, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.20', '6流定尺', 'real', 6, 92, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.20', '7流定尺', 'real', 6, 96, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.20', '8流定尺', 'real', 6, 100, 0, 4, TRUE, FALSE, 500, 2);

-- 插入炼钢PLC 172.16.1.21的数据点配置
INSERT INTO data_points (ip_address, name, type, db_number, start_offset, bit_offset, size, read_allow, write_allow, frequency, group_id) VALUES
('172.16.1.21', '5#结晶器流量', 'real', 16, 232, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#结晶器水温差', 'real', 16, 236, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#二冷水总管压力', 'real', 16, 240, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#结晶器进水温度', 'real', 16, 244, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#结晶器水压', 'real', 16, 248, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#二冷水总管温度', 'real', 16, 252, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#水流量-1流-1段', 'real', 16, 0, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#水流量-1流-2段', 'real', 16, 4, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#水流量-1流-3段', 'real', 16, 8, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#水流量-1流-4段', 'real', 16, 12, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#水流量-1流-5段', 'real', 16, 16, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#水流量-2流-1段', 'real', 16, 20, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#水流量-2流-2段', 'real', 16, 24, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#水流量-2流-3段', 'real', 16, 28, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#水流量-2流-4段', 'real', 16, 32, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#水流量-2流-5段', 'real', 16, 36, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#水流量-3流-1段', 'real', 16, 40, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#水流量-3流-2段', 'real', 16, 44, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#水流量-3流-3段', 'real', 16, 48, 0, 4, TRUE, FALSE, 500, 1),
('172.16.1.21', '5#水流量-3流-4段', 'real', 16, 52, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-3流-5段', 'real', 16, 56, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-4流-1段', 'real', 16, 60, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-4流-2段', 'real', 16, 64, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-4流-3段', 'real', 16, 68, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-4流-4段', 'real', 16, 72, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-4流-5段', 'real', 16, 76, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-5流-1段', 'real', 16, 80, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-5流-2段', 'real', 16, 84, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-5流-3段', 'real', 16, 88, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-5流-4段', 'real', 16, 92, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-5流-5段', 'real', 16, 96, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-6流-1段', 'real', 16, 100, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-6流-2段', 'real', 16, 104, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-6流-3段', 'real', 16, 108, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-6流-4段', 'real', 16, 112, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-6流-5段', 'real', 16, 116, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-7流-1段', 'real', 16, 120, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-7流-2段', 'real', 16, 124, 0, 4, TRUE, FALSE, 500, 2),
('172.16.1.21', '5#水流量-7流-3段', 'real', 16, 128, 0, 4, TRUE, FALSE, 500, 3),
('172.16.1.21', '5#水流量-7流-4段', 'real', 16, 132, 0, 4, TRUE, FALSE, 500, 3),
('172.16.1.21', '5#水流量-7流-5段', 'real', 16, 136, 0, 4, TRUE, FALSE, 500, 3),
('172.16.1.21', '5#水流量-8流-1段', 'real', 16, 140, 0, 4, TRUE, FALSE, 500, 3),
('172.16.1.21', '5#水流量-8流-2段', 'real', 16, 144, 0, 4, TRUE, FALSE, 500, 3),
('172.16.1.21', '5#水流量-8流-3段', 'real', 16, 148, 0, 4, TRUE, FALSE, 500, 3),
('172.16.1.21', '5#水流量-8流-4段', 'real', 16, 152, 0, 4, TRUE, FALSE, 500, 3),
('172.16.1.21', '5#水流量-8流-5段', 'real', 16, 156, 0, 4, TRUE, FALSE, 500, 3);

-- 初始化炼钢实时数据表
-- dint类型数据点
INSERT INTO realtime_data (point_id, int_value, timestamp)
SELECT id, 0, NOW(3) FROM data_points WHERE type = 'dint';

-- real类型数据点
INSERT INTO realtime_data (point_id, real_value, timestamp)
SELECT id, 0.0, NOW(3) FROM data_points WHERE type = 'real';
