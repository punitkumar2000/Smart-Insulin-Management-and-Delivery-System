"""Small explicit min-heap used to prioritize patients by days of supply."""

class MinHeap:
    def __init__(self):
        self.items = []

    def push(self, priority, item):
        self.items.append((float(priority), item))
        self._up(len(self.items) - 1)

    def _up(self, i):
        while i:
            p = (i - 1) // 2
            if self.items[p][0] <= self.items[i][0]: break
            self.items[p], self.items[i] = self.items[i], self.items[p]
            i = p

    def _down(self, i):
        n = len(self.items)
        while 2 * i + 1 < n:
            child = 2 * i + 1
            if child + 1 < n and self.items[child + 1][0] < self.items[child][0]: child += 1
            if self.items[i][0] <= self.items[child][0]: break
            self.items[i], self.items[child] = self.items[child], self.items[i]
            i = child

    def pop(self):
        if not self.items: return None
        root = self.items[0]
        tail = self.items.pop()
        if self.items:
            self.items[0] = tail
            self._down(0)
        return root

