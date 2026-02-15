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
#from gpiozero import LED
import time

cap = cv2.VideoCapture(0)
detector = FaceMeshDetector(maxFaces=1)
plotY = LivePlot(640,480, [20,50])
alertbackground = cv2.imread('BG.jpeg', 0)
alertbackground = cv2.resize(alertbackground, (1000, 500))
#led = LED(17)


idList = [22,23,24,26,110,157,158,159,160,161,130,243] #252,253,254,339,384,385,386,387,388]
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
Alarmcooldown = 0
slowblinking = 0
slowblinkingcounter = 0
slowblinked = 0


class DrowsinessAlert:
    def __init__(self):
        self.root = tk.Toplevel() if tk._default_root else tk.Tk()
        self.root.title("Drowsiness Alert")
        self.root.attributes('-fullscreen', True)
        self.root.state('zoomed')
        self.is_destroyed = False
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
            if os.path.exists(icon_path):
                icon = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(False, icon)
        except:
            pass
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.setup_background()
        self.countdown = 10
        self.timer_running = True
        self.create_widgets()
        self.update_timer()
    def bring_to_front(self):
        if not self.is_destroyed and self.root.winfo_exists():
            try:
                self.root.lift()
                self.root.attributes('-topmost', True)
                self.root.focus_force()
                self.root.grab_set()
                #self.root.after(500, lambda: self.safe_remove_topmost())
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
            bg_path = os.path.join(os.path.dirname(__file__), "BG.jpeg")
            if os.path.exists(bg_path):
                bg_image = Image.open(bg_path)
                bg_image = bg_image.resize((self.screen_width, self.screen_height), Image.Resampling.LANCZOS)
                self.bg_photo = ImageTk.PhotoImage(bg_image)
                bg_label = tk.Label(self.root, image=self.bg_photo)
                bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            else:
                self.root.configure(bg='white')
        except:
            self.root.configure(bg='white')
    def create_widgets(self):
        self.main_text = tk.Label(
            self.root,
            text="Drowsiness Detected: Start vibration?",
            font=("Arial", 24),
            fg="black",
            bg="white"
        )
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
        global Existingalarm, Alarm
        Alarm = False
        Existingalarm = False
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
        img, faces = detector.findFaceMesh(img, draw=False)

        if faces:
            face = faces[0]
            for id in idList:
                cv2.circle(img, face[id], 5, (255,0,255), cv2.FILLED)

            leftUp = face[159]
            leftDown = face[23]
            leftleft = face[130]
            leftright = face[243]
            LenghtVertical, _ = detector.findDistance(leftUp, leftDown)
            LenghtHorizontal, _ = detector.findDistance(leftleft, leftright)
            cv2.line(img, leftUp, leftDown, (0,200,0), 3)
            cv2.line(img, leftleft, leftright, (0,200,0), 3)

            ratio = (LenghtVertical/LenghtHorizontal)*100
            Ratiolist.append(ratio)
            if len(Ratiolist) > 3:
                Ratiolist.pop(0)
            AverageRatio = sum(Ratiolist)/len(Ratiolist)
            if len(Overtime) > 3600: #considering 60fps, 1 minute
                Overtime.pop(0)
                Sampled = True
            SumOvertime = sum(Overtime)

            Alarmcooldown += 1

            if 7 > SumOvertime > 3 and Alarm == False and Sampled == True and Alarmcooldown > 50:
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


            if AverageRatio < Threshold: #eye closed
                EyeClosed += 1
                slowblinking += 3
            else:
                EyeClosed = 0
                slowblinking -= 1
                slowblinked = 0

            if EyeClosed > 90 and Alarm == False and Alarmcooldown > 50:
                Alarm = True
                Trigger = True

            if slowblinking < 0:
                slowblinking = 0

            if slowblinking > 100 and slowblinked == 0:
                slowblinked = 1
                slowblinkingcounter += 1

            if slowblinkingcounter > 20 and Alarm == False and Alarmcooldown > 50:
                Alarm = True
                slowblinkingcounter = 0


            print(slowblinking)

            imageplot = plotY.update(AverageRatio)
            img = cv2.resize(img, ((640 * 1), (480 * 1)))
            imagestack = cvzone.stackImages([img, imageplot], 2, 1)

        else:
            img = cv2.resize(img, ((640 * 1), (480 * 1)))
            imagestack = cvzone.stackImages([img, img], 2, 1)

                          #change later
        #img = cv2.flip(img, 1)
        cv2.imshow("DrowsyCam", imagestack)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    if Alarm == True and Existingalarm == False and Alarmcooldown > 50:
        Alarmcooldown = 0
        Existingalarm = True
        Alert = DrowsinessAlert()
        Alert.bring_to_front()
        Alert.run()

    if Trigger == True:
        #led.on()
        time.sleep(10)
        #led.off()
        Trigger = False


cap.release()
cv2.destroyAllWindows()
