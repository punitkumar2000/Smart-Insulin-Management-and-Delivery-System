"""Supply calculations and threshold classification."""
def remaining_days(units, average):
    return max(0.0, float(units)) / float(average) if average and average > 0 else float("inf")

def threshold(days):
    if days <= 3:
        return "Emergency", "red"
    if days <= 5:
        return "Critical", "orange"
    if days <= 7:
        return "Warning", "yellow"
    return "Sufficient Supply", "green"

