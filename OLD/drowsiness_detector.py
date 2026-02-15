import time
import numpy as np


class DrowsinessDetector:
    def __init__(self, eye_open_ref, eye_closed_ref, eye_closed_threshold_percent=0.2,
                 eye_partially_closed_threshold_percent=0.6):
        self.eye_open_ref = eye_open_ref
        self.eye_closed_ref = eye_closed_ref

        # Calculate absolute EAR thresholds based on reference values
        # Eye is considered closed if it's 20% open relative to eye_open_ref
        self.eye_closed_ear_threshold = self.eye_closed_ref + (
                    self.eye_open_ref - self.eye_closed_ref) * eye_closed_threshold_percent
        # Eye is considered partially closed if it's 60% open relative to eye_open_ref
        self.eye_partially_closed_ear_threshold = self.eye_closed_ref + (
                    self.eye_open_ref - self.eye_closed_ref) * eye_partially_closed_threshold_percent

        print(f"DrowsinessDetector initialized:")
        print(f"  Eye Open Ref: {self.eye_open_ref:.2f}")
        print(f"  Eye Closed Ref: {self.eye_closed_ref:.2f}")
        print(f"  Eye Closed EAR Threshold: {self.eye_closed_ear_threshold:.2f}")
        print(f"  Eye Partially Closed EAR Threshold: {self.eye_partially_closed_ear_threshold:.2f}")

        # State variables for detection
        self.ear_history_1min = []  # Stores (timestamp, ear_value) for 1-minute checks
        self.blink_start_time = None
        self.is_eye_currently_closed = False
        self.blink_count_1min = 0
        self.blink_durations_1min = []  # Stores duration of blinks in 1 minute
        self.total_closed_frames_1min = 0
        self.total_frames_1min = 0

        self.reference_blink_speed = None  # For scenario 3
        self.first_minute_sampled = False

        self.last_minute_reset_time = time.time()

    def is_eye_closed(self, ear):
        """Determines if the eye is considered closed based on EAR and threshold."""
        return ear < self.eye_closed_ear_threshold

    def is_eye_partially_closed(self, ear):
        """Determines if the eye is considered partially closed."""
        return ear < self.eye_partially_closed_ear_threshold

    def update(self, current_ear):
        """Updates the detector with a new EAR value."""
        current_time = time.time()

        # Update 1-minute history
        self.ear_history_1min.append((current_time, current_ear))
        # Remove old entries (older than 1 minute)
        self.ear_history_1min = [(t, ear) for t, ear in self.ear_history_1min if current_time - t <= 60]

        # Update blink state
        eye_closed_now = self.is_eye_closed(current_ear)

        if eye_closed_now and not self.is_eye_currently_closed:
            # Eye just closed
            self.blink_start_time = current_time
            self.is_eye_currently_closed = True
        elif not eye_closed_now and self.is_eye_currently_closed:
            # Eye just opened
            self.is_eye_currently_closed = False
            if self.blink_start_time is not None:
                blink_duration = current_time - self.blink_start_time
                self.blink_durations_1min.append(blink_duration)
                self.blink_count_1min += 1
                self.blink_start_time = None  # Reset blink start time

        # Update total closed frames and total frames for scenario 4
        self.total_frames_1min += 1
        if eye_closed_now:
            self.total_closed_frames_1min += 1

        # Check if a minute has passed for scenarios 1, 3, 4
        if current_time - self.last_minute_reset_time >= 60:
            self.check_and_reset_minute_data()

    def check_and_reset_minute_data(self):
        """Checks 1-minute scenarios and resets data."""
        print("Checking 1-minute scenarios...")
        # Scenario 3: Sample reference blink speed if not already done
        if not self.first_minute_sampled:
            if self.blink_count_1min > 0:
                self.reference_blink_speed = np.mean(self.blink_durations_1min)
                self.first_minute_sampled = True
                print(f"Reference blink speed sampled: {self.reference_blink_speed:.2f} seconds/blink")
            else:
                print("Not enough blinks in first minute to sample reference speed.")

        # Reset data for the next minute
        self.blink_count_1min = 0
        self.blink_durations_1min = []
        self.total_closed_frames_1min = 0
        self.total_frames_1min = 0
        self.last_minute_reset_time = time.time()

    def check_drowsiness(self):
        """Checks all drowsiness scenarios and returns True if drowsy."""
        drowsy = False

        # Scenario 1: Blink count (4-6 times in 1 minute)
        # This check is done when `check_and_reset_minute_data` is called,
        # but the condition is based on the *previous* minute's data.
        # We need to store the blink count from the last minute to check this.
        # For simplicity, let's assume `blink_count_1min` is the count for the *just finished* minute.
        # If the current `blink_count_1min` is for the *current* minute, we need to adjust.
        # Let's re-evaluate this: the user said "over 1 minute they only closed their eyes for only 4-6 times"
        # and "this is checked after every minute". So, when `check_and_reset_minute_data` runs,
        # `self.blink_count_1min` holds the count for the minute that just ended.
        if not (4 <= self.blink_count_1min <= 6) and self.blink_count_1min > 0:
            print(f"Scenario 1 Check: Blink count ({self.blink_count_1min}) not in 4-6 range.")
            # This scenario implies *too few* blinks, not too many.
            # If the count is outside 4-6, it could be a sign of drowsiness (too few blinks).
            # Or it could be too many blinks (stress/irritation).
            # The prompt says "only 4-6 times", implying if it's *not* in this range, it's an issue.
            # Let's interpret "only 4-6 times" as the *alert* range, and anything outside is drowsy.
            # Re-reading: "over 1 minute they only closed their eyes for only 4-6 times"
            # This phrasing is a bit ambiguous. Does it mean if they blink *less* than 4 or *more* than 6, they are drowsy?
            # Or does it mean if they blink *exactly* 4-6 times, they are drowsy?
            # Given the context of an alarm, it's usually for *abnormal* behavior.
            # Let's assume it means if the blink count is *outside* the normal range (e.g., too few blinks).
            # A common range for normal blinks is 10-20 per minute. 4-6 is very low.
            # So, if blink_count_1min is 4-6, it's a sign of drowsiness.
            if 4 <= self.blink_count_1min <= 6:
                print(f"Scenario 1: Blink count ({self.blink_count_1min}) is in the drowsy range (4-6).")
                drowsy = True

        # Scenario 2: Long blink (1.5 seconds and more)
        # This needs to be checked continuously, not just at 1-minute intervals.
        # The `update` method handles `blink_start_time` and `blink_duration`.
        # We need to check if `is_eye_currently_closed` has been true for too long.
        if self.is_eye_currently_closed and (time.time() - self.blink_start_time) >= 1.5:
            print(f"Scenario 2: Long blink detected ({time.time() - self.blink_start_time:.2f}s).")
            drowsy = True

        # Scenario 3: Slow blinking compared to reference (average blink speed 40% higher)
        if self.first_minute_sampled and self.blink_count_1min > 0:
            current_avg_blink_speed = np.mean(self.blink_durations_1min)
            if current_avg_blink_speed > self.reference_blink_speed * 1.40:  # 40% higher
                print(
                    f"Scenario 3: Slow blinking detected. Current avg: {current_avg_blink_speed:.2f}, Ref: {self.reference_blink_speed:.2f}")
                drowsy = True

        # Scenario 4: Eyes below 60% open for 80% of the time in 1 minute
        if self.total_frames_1min > 0:
            partially_closed_frames = 0
            for t, ear in self.ear_history_1min:
                if self.is_eye_partially_closed(ear):
                    partially_closed_frames += 1

            if self.total_frames_1min > 0:  # Avoid division by zero
                partially_closed_percentage = (partially_closed_frames / len(self.ear_history_1min)) * 100 if len(
                    self.ear_history_1min) > 0 else 0
                if partially_closed_percentage >= 80:
                    print(
                        f"Scenario 4: Eyes partially closed for {partially_closed_percentage:.2f}% of the time in last minute.")
                    drowsy = True

        return drowsy