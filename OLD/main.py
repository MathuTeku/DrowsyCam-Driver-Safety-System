import tkinter as tk
from gui_windows import MainMenuWindow, RegisterNameWindow, RegistrationWindow, OperationWindow, AlertWindow
from gpio_controller import cleanup_gpio, init_gpio
import cv2
import threading
import time


class DrowsinessAlarmApp:
    def __init__(self, root):
        self.root = root
        # self.root.withdraw()  # REMOVED THIS LINE from here

        self.current_window = None
        self.cap = None  # Camera capture object
        self.video_thread = None
        self.video_running = False
        self.drowsiness_detector = None
        self.user_data = {}  # Stores eye_open_ref, eye_closed_ref for the logged-in user

        init_gpio()  # Initialize GPIO pins

        # Initialize the first window (MainMenuWindow)
        self.current_window = MainMenuWindow(self.root, self)
        self.current_window.show()  # This will call BaseWindow.show()

        # Now hide the main root window after the first Toplevel is shown
        self.root.withdraw()  # MOVED THIS LINE here

        # Handle window closing event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_camera(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("Error: Could not open camera.")
                self.cap = None
                return False
        self.video_running = True
        if self.video_thread is None or not self.video_thread.is_alive():
            self.video_thread = threading.Thread(target=self._video_loop, daemon=True)
            self.video_thread.start()
        return True

    def stop_camera(self):
        self.video_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.video_thread and self.video_thread.is_alive():
            self.video_thread.join(timeout=1)  # Wait for thread to finish

    def _video_loop(self):
        while self.video_running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to grab frame")
                break
            # Pass frame to the current window if it has a method to receive it
            if self.current_window and hasattr(self.current_window, 'update_frame'):
                self.current_window.update_frame(frame)
            time.sleep(0.01)  # Small delay to prevent busy-waiting

    def show_window(self, window_class, *args, **kwargs):
        # This method is for full-screen BaseWindow-derived classes
        if self.current_window:
            self.current_window.hide()
            # If it's the operation window, stop camera when hiding
            if isinstance(self.current_window, OperationWindow) or isinstance(self.current_window, RegistrationWindow):
                self.stop_camera()

        self.current_window = window_class(self.root, self, *args, **kwargs)
        self.current_window.show()  # BaseWindow.show() will be called here

        # If it's the operation or registration window, start camera
        if isinstance(self.current_window, OperationWindow) or isinstance(self.current_window, RegistrationWindow):
            self.start_camera()

    def show_main_menu(self):
        # This method is now just a wrapper to call show_window with MainMenuWindow
        # The initial display is handled in _init_
        self.show_window(MainMenuWindow)

    def show_register_name(self):
        # This method will handle RegisterNameWindow directly, as it's a modal dialog
        if self.current_window:
            self.current_window.hide()  # Hide the current full-screen window temporarily

        register_name_dialog = RegisterNameWindow(self.root, self)
        self.root.wait_window(register_name_dialog)  # Blocks until dialog is destroyed

        # After the dialog closes, check if a username was entered
        username = register_name_dialog.username_result
        if username:
            self.show_registration(username)  # Proceed to registration if name was entered
        else:
            self.show_main_menu()  # Go back to main menu if dialog was closed without entering a name

    def show_registration(self, username):
        self.show_window(RegistrationWindow, username)

    def show_operation(self, username, eye_open_ref, eye_closed_ref):
        self.user_data = {'username': username, 'eye_open_ref': eye_open_ref, 'eye_closed_ref': eye_closed_ref}
        self.show_window(OperationWindow, username, eye_open_ref, eye_closed_ref)

    def show_alert(self):
        # Pause operation window's detection loop
        if isinstance(self.current_window, OperationWindow):
            self.current_window.pause_detection()
        self.show_window(AlertWindow)

    def on_alert_closed(self):
        # Resume operation window's detection loop
        if isinstance(self.current_window, OperationWindow):
            self.current_window.resume_detection()

    def on_closing(self):
        print("Closing application...")
        self.stop_camera()
        cleanup_gpio()  # Clean up GPIO pins
        self.root.destroy()


if __name__ == "_main_":
    root = tk.Tk()
    app = DrowsinessAlarmApp(root)
    root.mainloop()
