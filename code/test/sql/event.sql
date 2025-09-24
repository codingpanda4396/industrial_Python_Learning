USE industrial_data;

-- 创建最近数据表
CREATE TABLE recent_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    point_id INT NOT NULL COMMENT '数据点ID',
    bool_value BOOLEAN NULL COMMENT '布尔值',
    int_value INT NULL COMMENT '整数值',
    real_value FLOAT NULL COMMENT '实数值',
    timestamp TIMESTAMP(3) NOT NULL COMMENT '数据时间戳(毫秒精度)',
    create_time TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '数据创建时间(毫秒精度)',
    FOREIGN KEY (point_id) REFERENCES data_points(id),
    INDEX (point_id, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='最近数据表';


DELIMITER //

CREATE EVENT purge_old_data
ON SCHEDULE EVERY 1 DAY 
STARTS TIMESTAMP(CURRENT_DATE, '01:00:00') + INTERVAL 1 DAY
COMMENT '每天凌晨删除昨天之前的所有数据'
DO
BEGIN
    -- 删除昨天之前的所有数据（保留昨天和今天的数据）
    DELETE FROM recent_data 
    WHERE timestamp < DATE_SUB(CURRENT_DATE, INTERVAL 1 DAY);
END//

DELIMITER ;