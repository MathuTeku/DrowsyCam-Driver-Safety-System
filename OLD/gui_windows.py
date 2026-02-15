import tkinter as tk
from tkinter import ttk, simpledialog
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import time
import threading
import numpy as np
import cv2  # <--- This import was added in the previous correction

from user_manager import list_users, save_user_data, load_user_data
from face_detection import get_largest_face_landmarks, ear_calculator, draw_landmarks
from drowsiness_detector import DrowsinessDetector
from gpio_controller import set_vibration, set_buzzer

# --- Constants ---
BG_IMAGE_PATH = "BG.jpeg"
FONT_FAMILY = "Arial"  # You can change this font
TEXT_COLOR = "black"
ALERT_TIMER_COLOR = "red"
EYE_CLOSED_THRESHOLD_PERCENT = 0.2  # Eye is considered closed if it's 20% open relative to eye_open_ref
EYE_PARTIALLY_CLOSED_THRESHOLD_PERCENT = 0.6  # Eye is considered 60% open relative to eye_open_ref
FRAME_AVERAGING_WINDOW = 3  # Number of frames to average for eye distance
ALERT_COOLDOWN_SECONDS = 10  # Cooldown for alert window


class BaseWindow(tk.Toplevel):
    def __init__(self, master, app_controller):
        super().__init__(master)
        self.app_controller = app_controller
        self.master = master
        self.withdraw()  # Hide initially

        self.attributes('-fullscreen', True)
        self.bind("<Escape>", lambda e: self.master.destroy())  # Exit on Escape (for testing)

        # Load background image
        try:
            self.bg_image_raw = Image.open(BG_IMAGE_PATH)
            self.bg_photo = None  # Will be updated on resize
            self.bind("<Configure>", self._on_resize)  # Bind resize event
        except FileNotFoundError:
            print(f"Warning: Background image '{BG_IMAGE_PATH}' not found. Using default background.")
            self.configure(bg="white")
            self.bg_image_raw = None

    def _on_resize(self, event):
        if self.bg_image_raw:
            width, height = self.winfo_width(), self.winfo_height()
            if width > 0 and height > 0:
                resized_image = self.bg_image_raw.resize((width, height), Image.LANCZOS)
                self.bg_photo = ImageTk.PhotoImage(resized_image)
                if hasattr(self, 'bg_label'):
                    self.bg_label.config(image=self.bg_photo)
                else:
                    self.bg_label = tk.Label(self, image=self.bg_photo)
                    self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                    self.bg_label.lower()  # Send to back

    def show(self):
        self.deiconify()
        self.master.withdraw()  # Hide main root window
        self._on_resize(None)  # Initial resize to fit screen

    def hide(self):
        self.withdraw()


class MainMenuWindow(BaseWindow):
    def __init__(self, master, app_controller):
        super().__init__(master, app_controller)
        self.title("Main Menu")

        # Ensure background label is created
        if self.bg_image_raw:
            self.bg_label = tk.Label(self, image=self.bg_photo)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            self.bg_label.lower()

        # Left (Login) Frame
        self.login_frame = tk.Frame(self, bg='white', bd=2, relief="groove")
        self.login_frame.place(relx=0.25, rely=0.25, relwidth=0.4, relheight=0.5, anchor='n')

        tk.Label(self.login_frame, text="Login", font=(FONT_FAMILY, 24, "bold"), fg=TEXT_COLOR, bg='white').pack(
            pady=(20, 10))

        self.user_dropdown = ttk.Combobox(self.login_frame, state="readonly", font=(FONT_FAMILY, 16))
        self.user_dropdown.pack(pady=10, padx=20, fill='x')
        self.update_user_list()

        tk.Button(self.login_frame, text="Load", font=(FONT_FAMILY, 18), command=self.load_user).pack(pady=20)

        # Right (Register) Frame
        self.register_frame = tk.Frame(self, bg='white', bd=2, relief="groove")
        self.register_frame.place(relx=0.75, rely=0.25, relwidth=0.4, relheight=0.5, anchor='n')

        tk.Label(self.register_frame, text="Register", font=(FONT_FAMILY, 24, "bold"), fg=TEXT_COLOR, bg='white').pack(
            pady=(20, 10))

        tk.Button(self.register_frame, text="Register New User", font=(FONT_FAMILY, 18),
                  command=self.app_controller.show_register_name).pack(expand=True, pady=20)

    def update_user_list(self):
        users = list_users()
        self.user_dropdown['values'] = users
        if users:
            self.user_dropdown.set(users[0])  # Select first user by default

    def load_user(self):
        selected_user = self.user_dropdown.get()
        if selected_user:
            try:
                eye_open_ref, eye_closed_ref = load_user_data(selected_user)
                print(f"Loaded user {selected_user}: Open={eye_open_ref}, Closed={eye_closed_ref}")
                self.app_controller.show_operation(selected_user, eye_open_ref, eye_closed_ref)
            except FileNotFoundError:
                tk.messagebox.showerror("Error", f"User data for {selected_user} not found.")
            except Exception as e:
                tk.messagebox.showerror("Error", f"Failed to load user data: {e}")
        else:
            tk.messagebox.showwarning("Warning", "Please select a user to load.")

    def show(self):
        super().show()
        self.update_user_list()  # Refresh user list every time main menu is shown


class RegisterNameWindow(tk.Toplevel):
    def __init__(self, master, app_controller):
        super().__init__(master)
        self.app_controller = app_controller
        self.title("Enter Name")
        self.geometry("400x200")
        self.transient(master)  # Make it appear on top of the main window
        self.grab_set()  # Make it modal
        self.protocol("WM_DELETE_WINDOW", self._on_closing)  # Handle closing

        tk.Label(self, text="Enter your name:", font=(FONT_FAMILY, 16), fg=TEXT_COLOR).pack(pady=20)
        self.name_entry = tk.Entry(self, font=(FONT_FAMILY, 16))
        self.name_entry.pack(pady=10, padx=20, fill='x')
        self.name_entry.focus_set()

        tk.Button(self, text="Confirm", font=(FONT_FAMILY, 14), command=self.confirm_name).pack(pady=20)

        self.username_result = None  # To store the name entered

    def confirm_name(self):
        username = self.name_entry.get().strip()
        if username:
            self.username_result = username  # Store the result
            self.destroy()  # Close this window
        else:
            tk.messagebox.showwarning("Input Error", "Please enter a name.")

    def _on_closing(self):
        self.destroy()  # Just destroy the window, main.py will handle next step


class RegistrationWindow(BaseWindow):
    def __init__(self, master, app_controller, username):
        super().__init__(master, app_controller)
        self.title("Registration")
        self.username = username
        self.current_step = 0
        self.eye_open_ref = None
        self.eye_closed_ref = None
        self.ear_history = []  # For 3-frame averaging during registration

        # Camera feed area (3/4 of vertical axis)
        self.camera_frame = tk.Frame(self, bg='black')
        self.camera_frame.place(relx=0, rely=0, relwidth=1, relheight=0.75)
        self.camera_label = tk.Label(self.camera_frame)
        self.camera_label.pack(expand=True, fill='both')

        # Control area (1/4 of vertical axis)
        self.control_frame = tk.Frame(self, bg='white')
        self.control_frame.place(relx=0, rely=0.75, relwidth=1, relheight=0.25)

        # Left segment: Instructions
        self.instruction_frame = tk.Frame(self.control_frame, bg='white', bd=1, relief="solid")
        self.instruction_frame.place(relx=0, rely=0, relwidth=1 / 3, relheight=1)
        self.instruction_label = tk.Label(self.instruction_frame, text="", font=(FONT_FAMILY, 18), fg=TEXT_COLOR,
                                          bg='white', wraplength=self.winfo_width() / 3 - 20)
        self.instruction_label.pack(expand=True, fill='both', padx=10, pady=10)

        # Middle segment: Value/Units
        self.value_frame = tk.Frame(self.control_frame, bg='white', bd=1, relief="solid")
        self.value_frame.place(relx=1 / 3, rely=0, relwidth=1 / 3, relheight=1)
        self.value_label = tk.Label(self.value_frame, text="EAR: N/A", font=(FONT_FAMILY, 20, "bold"), fg=TEXT_COLOR,
                                    bg='white')
        self.value_label.pack(expand=True, fill='both', padx=10, pady=10)

        # Right segment: Confirm Button
        self.confirm_frame = tk.Frame(self.control_frame, bg='white', bd=1, relief="solid")
        self.confirm_frame.place(relx=2 / 3, rely=0, relwidth=1 / 3, relheight=1)
        self.confirm_button = tk.Button(self.confirm_frame, text="Confirm", font=(FONT_FAMILY, 20),
                                        command=self.next_step)
        self.confirm_button.pack(expand=True, fill='both', padx=20, pady=20)

        self.update_instructions()

    def update_instructions(self):
        if self.current_step == 0:
            self.instruction_label.config(text="Step 1: Look at the camera with your eyes WIDE OPEN. Press Confirm.")
            self.confirm_button.config(state=tk.NORMAL)
        elif self.current_step == 1:
            self.instruction_label.config(text="Step 2: Fully CLOSE your eyes. Press Confirm.")
            self.confirm_button.config(state=tk.NORMAL)
        elif self.current_step == 2:
            self.instruction_label.config(text="Registration Complete! Saving data...")
            self.confirm_button.config(state=tk.DISABLED)
            self.save_and_exit()

    def next_step(self):
        if self.current_step == 0:
            if self.ear_history:
                self.eye_open_ref = np.mean(self.ear_history)
                print(f"Recorded Eye Open Ref: {self.eye_open_ref}")
                self.ear_history = []  # Reset for next step
                self.current_step = 1
                self.update_instructions()
            else:
                tk.messagebox.showwarning("Warning",
                                          "No face detected or EAR data collected. Please ensure your face is visible.")
        elif self.current_step == 1:
            if self.ear_history:
                self.eye_closed_ref = np.mean(self.ear_history)
                print(f"Recorded Eye Closed Ref: {self.eye_closed_ref}")
                self.ear_history = []  # Reset
                self.current_step = 2
                self.update_instructions()
            else:
                tk.messagebox.showwarning("Warning",
                                          "No face detected or EAR data collected. Please ensure your face is visible.")

    def save_and_exit(self):
        if self.eye_open_ref is not None and self.eye_closed_ref is not None:
            save_user_data(self.username, self.eye_open_ref, self.eye_closed_ref)
            tk.messagebox.showinfo("Success", f"User '{self.username}' registered successfully!")
        else:
            tk.messagebox.showerror("Error", "Failed to record eye reference values.")
        self.app_controller.show_main_menu()

    def update_frame(self, frame):
        # Process frame for face detection and EAR
        landmarks = get_largest_face_landmarks(frame)
        current_ear = None
        if landmarks:
            left_eye_ear = ear_calculator(landmarks[36:42])
            right_eye_ear = ear_calculator(landmarks[42:48])
            current_ear = (left_eye_ear + right_eye_ear) / 2.0

            # Add to history for averaging
            self.ear_history.append(current_ear)
            if len(self.ear_history) > FRAME_AVERAGING_WINDOW:
                self.ear_history.pop(0)  # Keep only the last N frames

            # Draw landmarks for visualization
            frame = draw_landmarks(frame, landmarks)

        # Display current EAR (averaged if enough history)
        display_ear = np.mean(self.ear_history) if self.ear_history else "N/A"
        self.value_label.config(text=f"EAR: {display_ear:.2f}")

        # Convert frame to PhotoImage for Tkinter
        cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv2image)

        # Resize image to fit camera_label
        img_width, img_height = img.size
        label_width = self.camera_label.winfo_width()
        label_height = self.camera_label.winfo_height()

        if label_width > 0 and label_height > 0:
            aspect_ratio = img_width / img_height
            if label_width / label_height > aspect_ratio:
                new_height = label_height
                new_width = int(new_height * aspect_ratio)
            else:
                new_width = label_width
                new_height = int(new_width / aspect_ratio)
            img = img.resize((new_width, new_height), Image.LANCZOS)

        imgtk = ImageTk.PhotoImage(image=img)
        self.camera_label.imgtk = imgtk
        self.camera_label.config(image=imgtk)


class OperationWindow(BaseWindow):
    def __init__(self, master, app_controller, username, eye_open_ref, eye_closed_ref):
        super().__init__(master, app_controller)
        self.title("Operation")
        self.username = username
        self.eye_open_ref = eye_open_ref
        self.eye_closed_ref = eye_closed_ref

        self.drowsiness_detector = DrowsinessDetector(
            eye_open_ref=self.eye_open_ref,
            eye_closed_ref=self.eye_closed_ref,
            eye_closed_threshold_percent=EYE_CLOSED_THRESHOLD_PERCENT,
            eye_partially_closed_threshold_percent=EYE_PARTIALLY_CLOSED_THRESHOLD_PERCENT
        )
        self.detection_active = True
        self.detection_paused = False  # To pause when alert window is active
        self.last_alert_time = 0  # For alert cooldown

        # Camera feed area (3/4 of vertical axis)
        self.camera_frame = tk.Frame(self, bg='black')
        self.camera_frame.place(relx=0, rely=0, relwidth=1, relheight=0.75)
        self.camera_label = tk.Label(self.camera_frame)
        self.camera_label.pack(expand=True, fill='both')

        # Control area (1/4 of vertical axis)
        self.control_frame = tk.Frame(self, bg='white')
        self.control_frame.place(relx=0, rely=0.75, relwidth=1, relheight=0.25)

        # Left segment: Vibration Intensity Slider
        self.intensity_frame = tk.Frame(self.control_frame, bg='white', bd=1, relief="solid")
        self.intensity_frame.place(relx=0, rely=0, relwidth=1 / 3, relheight=1)
        tk.Label(self.intensity_frame, text="Vibration Intensity", font=(FONT_FAMILY, 16), fg=TEXT_COLOR,
                 bg='white').pack(pady=10)
        self.intensity_slider = ttk.Scale(self.intensity_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                          command=self.update_vibration_intensity)
        self.intensity_slider.set(50)  # Default value
        self.intensity_slider.pack(pady=5, padx=20, fill='x')
        tk.Label(self.intensity_frame, text="(Currently High/Low Only)", font=(FONT_FAMILY, 10), fg="gray",
                 bg='white').pack()

        # Middle segment: Vibration Control Button
        self.vibration_control_frame = tk.Frame(self.control_frame, bg='white', bd=1, relief="solid")
        self.vibration_control_frame.place(relx=1 / 3, rely=0, relwidth=1 / 3, relheight=1)
        tk.Label(self.vibration_control_frame, text="Vibration Control", font=(FONT_FAMILY, 16), fg=TEXT_COLOR,
                 bg='white').pack(pady=10)
        self.vibration_state = False  # False = inactive (Start), True = active (Stop)
        self.vibration_button = tk.Button(self.vibration_control_frame, text="Start", font=(FONT_FAMILY, 20),
                                          command=self.toggle_vibration)
        self.vibration_button.pack(expand=True, fill='both', padx=20, pady=20)

        # Right segment: Exit Button
        self.exit_frame = tk.Frame(self.control_frame, bg='white', bd=1, relief="solid")
        self.exit_frame.place(relx=2 / 3, rely=0, relwidth=1 / 3, relheight=1)
        tk.Button(self.exit_frame, text="Exit Program", font=(FONT_FAMILY, 20),
                  command=self.app_controller.on_closing).pack(expand=True, fill='both', padx=20, pady=20)

    def update_vibration_intensity(self, value):
        # This slider currently only affects the on/off state via the button.
        # For future PWM implementation on GPIO 13, you would use this value:
        # pwm_duty_cycle = float(value) # 0-100
        # self.pwm_object.ChangeDutyCycle(pwm_duty_cycle) # Assuming you set up PWM on GPIO 13
        pass

    def toggle_vibration(self):
        self.vibration_state = not self.vibration_state
        if self.vibration_state:
            self.vibration_button.config(text="Stop")
            set_vibration(True)  # GPIO 17 HIGH
            print("Vibration ON (GPIO 17 HIGH)")
        else:
            self.vibration_button.config(text="Start")
            set_vibration(False)  # GPIO 17 LOW
            print("Vibration OFF (GPIO 17 LOW)")

    def pause_detection(self):
        self.detection_paused = True
        print("Drowsiness detection paused.")

    def resume_detection(self):
        self.detection_paused = False
        print("Drowsiness detection resumed.")

    def update_frame(self, frame):
        # Process frame for face detection and EAR
        landmarks = get_largest_face_landmarks(frame)
        current_ear = None
        if landmarks:
            left_eye_ear = ear_calculator(landmarks[36:42])
            right_eye_ear = ear_calculator(landmarks[42:48])
            current_ear = (left_eye_ear + right_eye_ear) / 2.0

            # Draw landmarks for visualization
            frame = draw_landmarks(frame, landmarks)

        # Only update detector if not paused
        if not self.detection_paused:
            if current_ear is not None:
                self.drowsiness_detector.update(current_ear)

            # Check for drowsiness
            if time.time() - self.last_alert_time > ALERT_COOLDOWN_SECONDS:
                if self.drowsiness_detector.check_drowsiness():
                    print("Drowsiness detected! Triggering alert.")
                    self.app_controller.show_alert()
                    self.last_alert_time = time.time()  # Reset cooldown timer

        # Convert frame to PhotoImage for Tkinter
        cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv2image)

        # Resize image to fit camera_label
        img_width, img_height = img.size
        label_width = self.camera_label.winfo_width()
        label_height = self.camera_label.winfo_height()

        if label_width > 0 and label_height > 0:
            aspect_ratio = img_width / img_height
            if label_width / label_height > aspect_ratio:
                new_height = label_height
                new_width = int(new_height * aspect_ratio)
            else:
                new_width = label_width
                new_height = int(new_width / aspect_ratio)
            img = img.resize((new_width, new_height), Image.LANCZOS)

        imgtk = ImageTk.PhotoImage(image=img)
        self.camera_label.imgtk = imgtk
        self.camera_label.config(image=imgtk)


class AlertWindow(BaseWindow):
    def __init__(self, master, app_controller):
        super().__init__(master, app_controller)
        self.title("Drowsiness Alert!")

        # Ensure background label is created
        if self.bg_image_raw:
            self.bg_label = tk.Label(self, image=self.bg_photo)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            self.bg_label.lower()

        # Main text
        self.alert_text_label = tk.Label(self, text="Drowsiness Detected: Start vibration?",
                                         font=(FONT_FAMILY, 36, "bold"), fg=TEXT_COLOR, bg='white')
        self.alert_text_label.place(relx=0.5, rely=0.4, anchor='center')  # Centered

        # Countdown timer
        self.countdown_value = 5
        self.countdown_label = tk.Label(self, text=f"{self.countdown_value}",
                                        font=(FONT_FAMILY, 72, "bold"), fg=ALERT_TIMER_COLOR, bg='white')
        self.countdown_label.place(relx=0.5, rely=0.55, anchor='center')  # Below main text

        # Buttons
        self.yes_button = tk.Button(self, text="YES", font=(FONT_FAMILY, 24, "bold"), command=self.activate_vibration)
        self.yes_button.place(relx=3 / 8, rely=3 / 4, anchor='center', width=150, height=70)

        self.no_button = tk.Button(self, text="NO", font=(FONT_FAMILY, 24, "bold"), command=self.close_alert)
        self.no_button.place(relx=5 / 8, rely=3 / 4, anchor='center', width=150, height=70)

        self.buzzer_thread = None
        self.buzzer_active = True
        self.start_buzzer()
        self.start_countdown()

    def start_buzzer(self):
        def buzzer_loop():
            while self.buzzer_active:
                set_buzzer(True)  # GPIO 27 HIGH
                time.sleep(1)
                set_buzzer(False)  # GPIO 27 LOW
                time.sleep(1)

        self.buzzer_thread = threading.Thread(target=buzzer_loop, daemon=True)
        self.buzzer_thread.start()

    def stop_buzzer(self):
        self.buzzer_active = False
        if self.buzzer_thread and self.buzzer_thread.is_alive():
            self.buzzer_thread.join(timeout=1)
        set_buzzer(False)  # Ensure buzzer is off

    def start_countdown(self):
        if self.countdown_value > 0:
            self.countdown_value -= 1
            self.countdown_label.config(text=f"{self.countdown_value}")
            self.after(1000, self.start_countdown)
        else:
            self.activate_vibration()  # Activate vibration when countdown reaches 0

    def activate_vibration(self):
        set_vibration(True)  # GPIO 17 HIGH
        print("Vibration activated by Alert Window (GPIO 17 HIGH)")
        self.close_alert()

    def close_alert(self):
        self.stop_buzzer()
        self.app_controller.on_alert_closed()
        self.destroy()  # Close the alert window
