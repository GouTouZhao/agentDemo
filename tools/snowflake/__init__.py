import time
import threading

class SnowflakeGenerator:
    """雪花算法 ID 生成器"""
    def __init__(self, datacenter_id: int, worker_id: int):
        self.datacenter_id = datacenter_id
        self.worker_id = worker_id
        self.sequence = 0
        self.last_timestamp = -1

        self.twepoch = 1288834974657
        self.worker_id_bits = 5
        self.datacenter_id_bits = 5
        self.sequence_bits = 12

        self.max_worker_id = -1 ^ (-1 << self.worker_id_bits)
        self.max_datacenter_id = -1 ^ (-1 << self.datacenter_id_bits)

        self.worker_id_shift = self.sequence_bits
        self.datacenter_id_shift = self.sequence_bits + self.worker_id_bits
        self.timestamp_left_shift = self.sequence_bits + self.worker_id_bits + self.datacenter_id_bits
        self.sequence_mask = -1 ^ (-1 << self.sequence_bits)

        self.lock = threading.Lock()

        if self.worker_id > self.max_worker_id or self.worker_id < 0:
            raise ValueError(f"worker_id can't be greater than {self.max_worker_id} or less than 0")
        if self.datacenter_id > self.max_datacenter_id or self.datacenter_id < 0:
            raise ValueError(f"datacenter_id can't be greater than {self.max_datacenter_id} or less than 0")

    def _get_timestamp(self) -> int:
        return int(time.time() * 1000)

    def _wait_next_millis(self, last_timestamp: int) -> int:
        timestamp = self._get_timestamp()
        while timestamp <= last_timestamp:
            timestamp = self._get_timestamp()
        return timestamp

    def next_id(self) -> int:
        with self.lock:
            timestamp = self._get_timestamp()

            if timestamp < self.last_timestamp:
                raise Exception(f"Clock moved backwards. Refusing to generate id for {self.last_timestamp - timestamp} milliseconds")

            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & self.sequence_mask
                if self.sequence == 0:
                    timestamp = self._wait_next_millis(self.last_timestamp)
            else:
                self.sequence = 0

            self.last_timestamp = timestamp

            new_id = ((timestamp - self.twepoch) << self.timestamp_left_shift) | \
                   (self.datacenter_id << self.datacenter_id_shift) | \
                   (self.worker_id << self.worker_id_shift) | \
                   self.sequence
            return new_id

# 全局唯一实例 (默认 datacenter_id=1, worker_id=1)
_global_snowflake = SnowflakeGenerator(datacenter_id=1, worker_id=1)

def gen_id() -> str:
    """
    生成全局唯一雪花 ID
    返回字符串类型，方便适配 VARCHAR(36) 的 UUID 兼容字段
    """
    return str(_global_snowflake.next_id())
