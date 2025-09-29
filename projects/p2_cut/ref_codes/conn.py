class PlcConnector:
    """
    PlcConnector 类负责与 PLC（可编程逻辑控制器）通信，核心目标是：
    1. **减少通信次数**：通过批量读取（read_all_once）一次性获取所有数据。
    2. **提供缓存机制**：避免在短时间内重复读取同样的地址，提高性能。
    3. **模拟模式支持**：如果没有真实 PLC，提供随机数模拟。
    """

    def __init__(self, plc_client, read_map, cache_ttl=0.5, simulate=False):
        """
        初始化连接器。

        :param plc_client: PLC 客户端对象，例如 snap7.client.Client()
        :param read_map: dict，键为逻辑名，值为 (db, start, size, type)
                         示例：{"flow": (1, 0, 4, 'REAL')}
        :param cache_ttl: 缓存的有效期（秒）
        :param simulate: 是否使用模拟模式（无 PLC 环境下调试）
        """
        self.client = plc_client
        self.read_map = read_map
        self.cache_ttl = cache_ttl
        self.simulate = simulate

        self._cache = {}  # {key: (timestamp, value)}

    def read(self, key):
        """
        读取单个参数。如果缓存存在且在 TTL 内，直接返回缓存值。
        否则执行一次 PLC 读取。
        """
        import time
        if key not in self.read_map:
            raise KeyError(f"未知的PLC键：{key}")

        now = time.time()
        if key in self._cache and now - self._cache[key][0] < self.cache_ttl:
            return self._cache[key][1]

        value = self._read_from_plc(key)
        self._cache[key] = (now, value)
        return value

    def _read_from_plc(self, key):
        """
        从 PLC 读取真实值（或模拟值）。
        """
        import random
        db, start, size, dtype = self.read_map[key]
        if self.simulate:
            if dtype == 'REAL':
                return random.uniform(0, 100)
            elif dtype == 'BOOL':
                return random.choice([True, False])
            elif dtype == 'INT':
                return random.randint(0, 32767)

        from snap7.util import get_real, get_int, get_bool
        data = self.client.db_read(db, start, size)

        if dtype == 'REAL':
            return get_real(data, 0)
        elif dtype == 'INT':
            return get_int(data, 0)
        elif dtype == 'BOOL':
            return get_bool(data, 0)
        else:
            raise TypeError(f"不支持的PLC类型：{dtype}")

    def read_all_once(self):
        """
        批量读取所有变量，一次性通信。
        结果会写入缓存并返回 dict。
        """
        import time
        import random
        now = time.time()
        results = {}

        if self.simulate:
            for key, (_, _, _, dtype) in self.read_map.items():
                if dtype == 'REAL':
                    results[key] = random.uniform(0, 100)
                elif dtype == 'BOOL':
                    results[key] = random.choice([True, False])
                elif dtype == 'INT':
                    results[key] = random.randint(0, 32767)
            self._cache = {k: (now, v) for k, v in results.items()}
            return results

        # --- 实际批量读取逻辑（按 DB 分组） ---
        from snap7.util import get_real, get_int, get_bool
        from collections import defaultdict

        grouped = defaultdict(list)
        for key, (db, start, size, dtype) in self.read_map.items():
            grouped[db].append((key, start, size, dtype))

        for db, items in grouped.items():
            # 找出该 DB 的最大范围
            start_min = min(i[1] for i in items)
            end_max = max(i[1] + i[2] for i in items)
            data = self.client.db_read(db, start_min, end_max - start_min)

            for key, start, size, dtype in items:
                offset = start - start_min
                if dtype == 'REAL':
                    value = get_real(data, offset)
                elif dtype == 'INT':
                    value = get_int(data, offset)
                elif dtype == 'BOOL':
                    value = get_bool(data, offset)
                else:
                    raise TypeError(f"不支持的PLC类型：{dtype}")
                results[key] = value

        # 缓存全部结果
        self._cache = {k: (now, v) for k, v in results.items()}
        return results
