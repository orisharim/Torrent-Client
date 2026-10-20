

class SpeedEstimator:

    def __init__(self, window_time : float = 3):
        self.window_time = window_time
        self.measurements = []

    def add_measurement(self, amount, timestamp):
        self.measurements.append((amount, timestamp))

    def get_estimated_speed(self, current_time):
        new_measurements = []
        for amount, timestamp in self.measurements:
            if current_time - timestamp <= self.window_time:
                new_measurements.append((amount, timestamp))
        self.measurements = new_measurements

        if not self.measurements:
            return 0.0

        total_amount = sum(amount for amount, _ in self.measurements)
        time_span = current_time - self.measurements[0][1]

        if time_span == 0:
            return 0.0

        return total_amount / time_span


        

    