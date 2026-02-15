import time
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("RPi.GPIO not found. Running in mock GPIO mode.")
    GPIO_AVAILABLE = False

# GPIO Pin Definitions
GPIO_VIBRATION_PIN = 17 # Connected to motor driver for vibration
# NOTE: User requested GPIO 13 for PWM later. For now, GPIO 17 is HIGH/LOW.
# When implementing PWM, you would change this to GPIO 13 and use GPIO.PWM.
# Example for PWM:
# pwm_vibration = GPIO.PWM(GPIO_VIBRATION_PIN, 100) # 100 Hz frequency
# pwm_vibration.start(0) # Start with 0% duty cycle
# To set intensity: pwm_vibration.ChangeDutyCycle(intensity_percentage)

GPIO_BUZZER_PIN = 27 # Connected to buzzer

def init_gpio():
    if GPIO_AVAILABLE:
        GPIO.setmode(GPIO.BCM) # Use Broadcom pin-numbering scheme
        GPIO.setup(GPIO_VIBRATION_PIN, GPIO.OUT)
        GPIO.setup(GPIO_BUZZER_PIN, GPIO.OUT)
        # Ensure pins are low initially
        GPIO.output(GPIO_VIBRATION_PIN, GPIO.LOW)
        GPIO.output(GPIO_BUZZER_PIN, GPIO.LOW)
        print("GPIO initialized.")
    else:
        print("Mock GPIO: Initialized.")

def set_vibration(state):
    """
    Sets the vibration motor state.
    state: True for HIGH (on), False for LOW (off).
    """
    if GPIO_AVAILABLE:
        GPIO.output(GPIO_VIBRATION_PIN, GPIO.HIGH if state else GPIO.LOW)
    else:
        print(f"Mock GPIO: Vibration set to {'HIGH' if state else 'LOW'} (Pin {GPIO_VIBRATION_PIN})")

def set_buzzer(state):
    """
    Sets the buzzer state.
    state: True for HIGH (on), False for LOW (off).
    """
    if GPIO_AVAILABLE:
        GPIO.output(GPIO_BUZZER_PIN, GPIO.HIGH if state else GPIO.LOW)
    else:
        print(f"Mock GPIO: Buzzer set to {'HIGH' if state else 'LOW'} (Pin {GPIO_BUZZER_PIN})")

def cleanup_gpio():
    if GPIO_AVAILABLE:
        GPIO.cleanup()
        print("GPIO cleaned up.")
    else:
        print("Mock GPIO: Cleaned up.")

# Example usage (for testing, not part of the main app flow)
if __name__ == "__main__":
    init_gpio()
    print("Testing vibration...")
    set_vibration(True)
    time.sleep(2)
    set_vibration(False)
    print("Testing buzzer...")
    set_buzzer(True)
    time.sleep(1)
    set_buzzer(False)
    cleanup_gpio()