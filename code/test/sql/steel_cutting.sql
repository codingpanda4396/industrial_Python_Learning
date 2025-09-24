CREATE TABLE steel_billet_monitoring (
    billet_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '拟合钢坯编号',
    strand_no TINYINT NOT NULL COMMENT '铸流编号',
    
    -- 时间参数
    cutting_time DATETIME NOT NULL COMMENT '钢坯开始切割时间',
    entry_time DATETIME NOT NULL COMMENT '钢坯进入结晶器前12m时间',
    exit_time DATETIME NOT NULL COMMENT '钢坯离开结晶器前12m时间',
    
    -- 冷却水参数
    water_temperature DECIMAL(5,2) COMMENT '二冷水平均水温',
    water_pressure DECIMAL(6,2) COMMENT '二冷水平均水压',
    water_volume DECIMAL(8,2) COMMENT '5段总水量',
    water_pressure_sd DECIMAL(6,2) COMMENT '二冷水水压标准差',
    
    -- 钢温度
    steel_temperature DECIMAL(7,2) COMMENT '平均钢温',

    -- 结晶器
    drawing_speed DECIMAL(7,2) COMMENT '平均拉速',
    water_temperature_difference DECIMAL(7,2) COMMENT '结晶器平均水温差',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    
    INDEX idx_cutting_time (cutting_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='钢坯拟合数据表';