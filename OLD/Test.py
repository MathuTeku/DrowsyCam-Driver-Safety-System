import numpy as np
import cv2
import cvzone
from cvzone.FaceMeshModule import FaceMeshDetector
from cvzone.PlotModule import LivePlot
import tkinter as tk
from PIL import Image, ImageTk
import os
from tkinter import *
import threading
#from gpiozero import LED # Keeping this commented as per your original code

import time
import subprocess  # New import for running rpicam-vid
import sys  # New import for sys.stderr
import stat  # New import for checking FIFO

# Define the path for the named pipe
PIPE_PATH = '/tmp/rpicam_fifo'  # Using /tmp is generally safe for temporary files

# --- Start: Camera Initialization with rpicam-vid streaming via Named Pipe ---
cap = None
rpicam_process = None
camera_opened = False

print("Initializing camera using rpicam-vid streaming via Named Pipe...", file=sys.stderr)

try:
    # 1. Create the named pipe (FIFO)
    if os.path.exists(PIPE_PATH):
        if stat.S_ISFIFO(os.stat(PIPE_PATH).st_mode):
            print(f"Named pipe '{PIPE_PATH}' already exists.", file=sys.stderr)
        else:
            print(f"Error: A non-FIFO file exists at '{PIPE_PATH}'. Removing it.", file=sys.stderr)
            os.remove(PIPE_PATH)
            os.mkfifo(PIPE_PATH)
    else:
        os.mkfifo(PIPE_PATH)
    print(f"Named pipe created at: {PIPE_PATH}", file=sys.stderr)

    # 2. rpicam-vid command to stream to the named pipe
    # Adjust width/height/framerate as needed for your camera and performance
    rpicam_cmd = [
        'rpicam-vid',
        '--timeout', '0',  # Run indefinitely
        '--width', '640',
        '--height', '480',
        '--framerate', '30',
        '--output', PIPE_PATH,  # Output to the named pipe
        '--codec', 'mjpeg',  # Use MJPEG codec
        '--nopreview'  # Don't show rpicam's own preview window
    ]

    print(f"Executing rpicam-vid command: {' '.join(rpicam_cmd)}", file=sys.stderr)
    # Start the rpicam process. stderr is captured for debugging.
    rpicam_process = subprocess.Popen(rpicam_cmd, stderr=subprocess.PIPE)
    print(f"rpicam-vid process started with PID: {rpicam_process.pid}", file=sys.stderr)

    # Give rpicam a moment to start streaming to the pipe
    time.sleep(2)

    # Check if the rpicam process is still running
    if rpicam_process.poll() is not None:
        stderr_output = rpicam_process.stderr.read().decode('utf-8')
        print(f"rpicam-vid process exited prematurely with code {rpicam_process.returncode}. Stderr: {stderr_output}",
              file=sys.stderr)
        raise RuntimeError("rpicam-vid process failed to start or exited early.")

    # 3. OpenCV VideoCapture reads from the named pipe
    print(f"Attempting to open OpenCV VideoCapture from named pipe: {PIPE_PATH}", file=sys.stderr)
    cap = cv2.VideoCapture(PIPE_PATH, cv2.CAP_FFMPEG)  # Use CAP_FFMPEG backend explicitly

    print(f"VideoCapture.isOpened() result: {cap.isOpened()}", file=sys.stderr)

    if cap.isOpened():
        # Test if we can actually read a frame
        ret, test_frame = cap.read()
        print(f"Initial cap.read() result: ret={ret}, frame is None={test_frame is None}", file=sys.stderr)
        if ret and test_frame is not None:
            print("Camera opened successfully using rpicam-vid streaming via Named Pipe!", file=sys.stderr)
            camera_opened = True
        else:
            print("Named pipe opened, but failed to read initial frame. Releasing resources.", file=sys.stderr)
            cap.release()
            rpicam_process.terminate()
            rpicam_process.wait()

except FileNotFoundError:
    print("Error: 'rpicam-vid' command not found.", file=sys.stderr)
    print("Please ensure Raspberry Pi OS is up to date and camera software is installed.", file=sys.stderr)
except Exception as e:
    print(f"Error with rpicam-vid streaming via Named Pipe: {e}", file=sys.stderr)

if not camera_opened:
    print("Error: Could not open camera with rpicam-vid streaming via Named Pipe.", file=sys.stderr)
    print("Falling back to direct OpenCV camera access (may not work for CSI camera).", file=sys.stderr)
    # Fallback to direct OpenCV access if rpicam-vid fails
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        ret, test_frame = cap.read()
        if ret and test_frame is not None:
            print("Camera opened successfully with direct OpenCV access!", file=sys.stderr)
            camera_opened = True
        else:
            cap.release()

if not camera_opened:
    print("Fatal Error: Could not open camera with any method. Exiting.", file=sys.stderr)
    print("Please ensure:", file=sys.stderr)
    print("1. Camera is properly connected and enabled in raspi-config.", file=sys.stderr)
    print("2. Try running 'rpicam-hello' in your terminal to test the camera independently.", file=sys.stderr)
    sys.exit(1)
# --- End: Camera Initialization with rpicam-vid streaming ---

detector = FaceMeshDetector(maxFaces=1)
plotY = LivePlot(640, 480, [20, 50])

try:
    from pygame import mixer

    mixer.init()
    alarm_wav_path = os.path.join(os.path.dirname(__file__), 'alarm.wav')
    if os.path.exists(alarm_wav_path):
        sound = mixer.Sound(alarm_wav_path)
    else:
        print(f"Warning: alarm.wav not found at {alarm_wav_path}. Alarm sound will not play.", file=sys.stderr)
        sound = None
except ImportError:
    print("Warning: pygame not found. Alarm sound will not play.", file=sys.stderr)
    sound = None
except Exception as e:
    print(f"Warning: Could not initialize pygame mixer or load alarm.wav: {e}", file=sys.stderr)
    sound = None

alertbackground_path = os.path.join(os.path.dirname(__file__), 'BG.jpg')
alertbackground = cv2.imread(alertbackground_path, 0)
if alertbackground is not None:
    alertbackground = cv2.resize(alertbackground, (1000, 500))
else:
    print(f"Warning: BG.jpg not found at {alertbackground_path} for alert background. Alert background will be black.",
          file=sys.stderr)
    alertbackground = np.zeros((500, 1000), dtype=np.uint8)  # Create a black background as fallback

#led = LED(17)

idList = [22, 23, 24, 26, 110, 157, 158, 159, 160, 161, 130, 243]  # 252,253,254,339,384,385,386,387,388]
Ratiolist = []
Overtime = []
blinkcounter = 0
blinkcooldown = 0
Threshold = 34
EyeClosed = 0
Alarm = False
Existingalarm = False
Test = 0
Operating = True
Mainmenu = False
Trigger = False
Alert = None
Sampled = False
Alarmcooldown = 100
slowblinking = 0
slowblinkingcounter = 0
slowblinked = 0


class DrowsinessAlert:
    def __init__(self):
        self.root = tk.Toplevel() if tk._default_root else tk.Tk()
        self.root.title("Drowsiness Alert")
        self.root.attributes('-fullscreen', True)
        # Removed: self.root.state('zoomed') # This line caused the error
        self.is_destroyed = False
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
            if os.path.exists(icon_path):
                icon = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(False, icon)
        except Exception as e:
            print(f"Warning: Could not load icon.png: {e}", file=sys.stderr)
            pass

        self.root.update_idletasks()
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        self.root.geometry(f"{self.screen_width}x{self.screen_height}+0+0")
        print(f"Alert window created with geometry: {self.screen_width}x{self.screen_height}", file=sys.stderr)

        self.setup_background()
        self.countdown = 3
        self.timer_running = True
        self.create_widgets()
        self.update_timer()

    def bring_to_front(self):
        if not self.is_destroyed and self.root.winfo_exists():
            try:
                self.root.lift()
                self.root.attributes('-topmost', True)
                # Removed: self.root.focus_force()
                # Removed: self.root.grab_set()
                # self.root.after(500, lambda: self.safe_remove_topmost())
            except tk.TclError:
                self.is_destroyed = True

    def safe_remove_topmost(self):
        if not self.is_destroyed and self.root.winfo_exists():
            try:
                self.root.attributes('-topmost', False)
            except tk.TclError:
                self.is_destroyed = True

    def on_window_close(self):
        self.is_destroyed = True
        self.root.destroy()

    def setup_background(self):
        try:
            bg_path = os.path.join(os.path.dirname(__file__), "BG.jpg")
            if os.path.exists(bg_path):
                bg_image = Image.open(bg_path)
                bg_image = bg_image.resize((self.screen_width, self.screen_height), Image.Resampling.LANCZOS)
                self.bg_photo = ImageTk.PhotoImage(bg_image)
                bg_label = tk.Label(self.root, image=self.bg_photo)
                bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            else:
                self.root.configure(bg='white')
                print(f"Warning: BG.jpg not found at {bg_path} for DrowsinessAlert background. Using white background.",
                      file=sys.stderr)
        except Exception as e:
            self.root.configure(bg='white')
            print(f"Error loading DrowsinessAlert background image: {e}. Using white background.", file=sys.stderr)

    def create_widgets(self):
        self.main_text = tk.Label(
            self.root,
            text="Drowsiness Detected: Start vibration?",
            font=("Arial", 24),
            fg="black",
            bg="white")
        self.root.update_idletasks()
        text_width = self.main_text.winfo_reqwidth()
        text_x = (self.screen_width - text_width) // 2
        text_y = self.screen_height // 2 - 50
        self.main_text.place(x=text_x, y=text_y)
        self.timer_text = (tk.Label(
            self.root,
            text=str(self.countdown),
            font=("Arial", 24),
            fg="red",
            bg="white"
        ))
        timer_x = self.screen_width // 2
        timer_y = text_y + 60
        self.timer_text.place(x=timer_x, y=timer_y, anchor="center")
        self.yes_button = tk.Button(
            self.root,
            text="YES",
            font=("Arial", 16),
            command=self.yes_pressed,
            width=10,
            height=2
        )
        yes_x = (3 * self.screen_width) // 8
        yes_y = (3 * self.screen_height) // 4
        self.yes_button.place(x=yes_x, y=yes_y, anchor="center")
        self.no_button = tk.Button(
            self.root,
            text="NO",
            font=("Arial", 16),
            command=self.no_pressed,
            width=10,
            height=2
        )
        no_x = (5 * self.screen_width) // 8
        no_y = (3 * self.screen_height) // 4
        self.no_button.place(x=no_x, y=no_y, anchor="center")

    def update_timer(self):
        if not self.is_destroyed and self.timer_running and self.countdown > 0:
            try:
                self.timer_text.config(text=str(self.countdown))
                self.countdown -= 1
                self.root.after(1000, self.update_timer)
            except tk.TclError:
                self.is_destroyed = True
        elif not self.is_destroyed and self.timer_running and self.countdown == 0:
            try:
                self.timer_text.config(text="0")
                self.timer_running = False
                global Trigger
                Trigger = True
                #led.on()--------------------------------
            except tk.TclError:
                self.is_destroyed = True

    def yes_pressed(self):
        global Trigger, Existingalarm, Alarm
        Alarm = False
        Existingalarm = False
        Trigger = True
        self.is_destroyed = True
        self.root.destroy()

    def no_pressed(self):
        global Existingalarm, Alarm, Trigger
        Alarm = False
        Existingalarm = False
        Trigger = False
        self.is_destroyed = True
        self.root.destroy()

    def run(self):
        self.root.mainloop()


while True:
    if Mainmenu == True:
        cv2.namedWindow("DrowsyCam")
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    if Operating == True:
        success, img = cap.read()
        if not success:
            print("Failed to grab frame. Exiting loop.", file=sys.stderr)
            break

        img, faces = detector.findFaceMesh(img, draw=True)
        if faces:
            face = faces[0]
            for id in idList:
                cv2.circle(img, face[id], 5, (255, 0, 255), cv2.FILLED)
            leftUp = face[159]
            leftDown = face[23]
            leftleft = face[130]
            leftright = face[243]
            LenghtVertical, _ = detector.findDistance(leftUp, leftDown)
            LenghtHorizontal, _ = detector.findDistance(leftleft, leftright)
            cv2.line(img, leftUp, leftDown, (0, 200, 0), 3)
            cv2.line(img, leftleft, leftright, (0, 200, 0), 3)
            ratio = (LenghtVertical / LenghtHorizontal) * 100
            Ratiolist.append(ratio)
            if len(Ratiolist) > 3:
                Ratiolist.pop(0)
            AverageRatio = sum(Ratiolist) / len(Ratiolist)
            if len(Overtime) > 3600:  # considering 60fps, 1 minute
                Overtime.pop(0)
                Sampled = True
            SumOvertime = sum(Overtime)
            Alarmcooldown += 1
            #led.off()----------------------------
            if 7 > SumOvertime > 3 and Alarm == False and Sampled == True and Alarmcooldown > 100:
                Alarm = True
                Sampled = False
                SumOvertime = 0
            if AverageRatio < Threshold and blinkcooldown > 15:
                blinkcounter += 1
                blinkcooldown = 0
                Overtime.append(1)
            else:
                blinkcooldown += 1
                Overtime.append(0)
            if AverageRatio < Threshold:  # eye closed
                EyeClosed += 1
                slowblinking += 3
            else:
                EyeClosed = 0
                slowblinking -= 1
                slowblinked = 0
            if EyeClosed > 60:
                Alarm = True
                EyeClosed = 0
            if slowblinking < 0:
                slowblinking = 0
            if slowblinking > 100 and slowblinked == 0:
                slowblinked = 1
                slowblinkingcounter += 1
            if slowblinkingcounter > 20 and Alarm == False and Alarmcooldown > 100:
                Alarm = True
                slowblinking = 0
                slowblinkingcounter = 0

            if Alarmcooldown < 100:
                Alarm = False

            print(slowblinking)
            imageplot = plotY.update(AverageRatio)
            img = cv2.resize(img, ((640 * 1), (480 * 1)))
            imagestack = cvzone.stackImages([img, imageplot], 2, 1)
        else:
            img = cv2.resize(img, ((640 * 1), (480 * 1)))
            imagestack = cvzone.stackImages([img, img], 2, 1)  # change later
        # img = cv2.flip(img, 1)
        cv2.imshow("DrowsyCam", imagestack)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    if Alarm == True and Existingalarm == False and Alarmcooldown > 100:
        Alarmcooldown = 0
        Existingalarm = True
        Alert = DrowsinessAlert()
        Alert.bring_to_front()
        Alert.run()
    if Trigger == True:
        #led.on()
        time.sleep(5)
        #led.off()
        Trigger = False

cap.release()
cv2.destroyAllWindows()

if rpicam_process:
    rpicam_process.terminate()
    rpicam_process.wait(timeout=5)  # Wait for process to terminate
    if rpicam_process.poll() is None:  # If it's still running-
        rpicam_process.kill()  # Force kill
    print("rpicam-vid process terminated.", file=sys.stderr)
# Clean up the named pipe
if os.path.exists(PIPE_PATH):
    try:
        os.remove(PIPE_PATH)
        print(f"Named pipe '{PIPE_PATH}' removed.", file=sys.stderr)
    except OSError as e:
        print(f"Error removing named pipe '{PIPE_PATH}': {e}", file=sys.stderr)
