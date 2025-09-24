-- INSERT INTO data_points(ip_address, name, type, db_number, start_offset, bit_offset, size, read_allow, write_allow, frequency, group_id) VALUES
-- ('192.168.1.215', '1流定尺反馈补偿量', 'int', 100, 28, 0, 2, TRUE, FALSE, 500, 1),
-- ('192.168.1.215', '2流定尺反馈补偿量', 'int', 100, 30, 0, 2, TRUE, FALSE, 500, 1),
-- ('192.168.1.215', '3流定尺反馈补偿量', 'int', 100, 32, 0, 2, TRUE, FALSE, 500, 1),
-- ('192.168.1.215', '4流定尺反馈补偿量', 'int', 100, 34, 0, 2, TRUE, FALSE, 500, 1),
-- ('192.168.1.215', '5流定尺反馈补偿量', 'int', 101, 28, 0, 2, TRUE, FALSE, 500, 1),
-- ('192.168.1.215', '6流定尺反馈补偿量', 'int', 101, 30, 0, 2, TRUE, FALSE, 500, 1),
-- ('192.168.1.215', '7流定尺反馈补偿量', 'int', 101, 32, 0, 2, TRUE, FALSE, 500, 1),
-- ('192.168.1.215', '8流定尺反馈补偿量', 'int', 101, 34, 0, 2, TRUE, FALSE, 500, 1);

-- INSERT INTO realtime_data(point_id, int_value, timestamp) VALUES
-- SELECT id, 0.0, NOW(3) FROM data_points WHERE ip_address = '192.168.1.215';

INSERT INTO data_points(ip_address, name, type, db_number, start_offset, bit_offset, size, read_allow, write_allow, frequency, group_id) VALUES
('192.168.1.215', '炉号', 'dint', 420, 34, 0, 4, TRUE, FALSE, 500, 1),

INSERT INTO realtime_data(point_id, int_value, timestamp)
SELECT id, 0, NOW(3) FROM data_points WHERE name = '炉号';

INSERT INTO data_points(ip_address, name, type, db_number, start_offset, bit_offset, size, read_allow, write_allow, frequency, group_id) VALUES
('192.168.0.3', '触发信号', 'bool', 889, 0, 3, 1, TRUE, FALSE, 500, 4),
('192.168.0.3', '取样标志', 'int', 889, 40, 0, 2, TRUE, FALSE, 500, 4);

INSERT INTO realtime_data(point_id, int_value, timestamp)
SELECT id, 0, NOW(3) FROM data_points WHERE name = '触发信号';

INSERT INTO realtime_data(point_id, int_value, timestamp)
SELECT id, 0, NOW(3) FROM data_points WHERE name = '取样标志';