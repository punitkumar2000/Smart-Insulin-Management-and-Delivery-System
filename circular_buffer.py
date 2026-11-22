"""Fixed-size circular buffer for daily insulin consumption."""

class CircularBuffer:
    CAPACITY = 5

    def __init__(self, values=None, index=0):
        self.values = list(values or [])[-self.CAPACITY:]
        self.index = int(index) % self.CAPACITY

    def add(self, value):
        value = float(value)
        if value < 0:
            raise ValueError("Consumption cannot be negative.")
        if len(self.values) < self.CAPACITY:
            self.values.append(value)
            self.index = len(self.values) % self.CAPACITY
        else:
            self.values[self.index] = value
            self.index = (self.index + 1) % self.CAPACITY
        return list(self.values)

    @property
    def ordered_values(self):
        """Return readings oldest-to-newest, including after the ring wraps."""
        if len(self.values) < self.CAPACITY:
            return list(self.values)
        return self.values[self.index:] + self.values[:self.index]

    @property
    def total(self):
        return sum(self.values)

    @property
    def average(self):
        return self.total / len(self.values) if self.values else 0.0
