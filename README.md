# DrowsyCam-Driver-Safety-System
DrowsyCam: Driver Safety System with Eye Recognition and Drowsiness Detection

DrowsyCam is a standalone, embedded driver-monitoring system designed to detect early signs of fatigue using real-time computer vision and motion sensing. The system operates on a Raspberry Pi 5 and utilizes the MediaPipe Face Mesh pre-trained model to extract 468 facial landmarks for accurate ocular feature analysis.

The software continuously calculates eye aspect ratios to identify physiological indicators of drowsiness, including:

Prolonged eye closure

Frequent blinking

Drooping eyelids (PERCLOS-based detection)

To reduce false alarms, DrowsyCam integrates an MPU-9250 accelerometer and gyroscope module that provides vehicle motion context. Detection logic is conditionally enabled only during valid driving states (e.g., not stationary or turning).

When fatigue is detected, the system activates a multi-stage alert mechanism:

Visual warning overlay

Audio alert

Seat vibration motor (if unacknowledged)

The project emphasizes affordability, portability, and real-time performance, offering a cost-effective alternative to luxury vehicle ADAS systems.

Technical Highlights

Pre-trained MediaPipe Face Mesh (468 landmark model)

Real-time eye ratio computation and temporal smoothing

Rolling window blink and droop event analysis

Motion-aware false detection prevention

Touchscreen-based driver calibration system

Lightweight file-based driver profile storage

Fully offline operation

Hardware Components

Raspberry Pi 5

Raspberry Pi Camera Module

MPU-9250 (9-axis IMU)

Touchscreen display

Vibration motor module

5V regulated power supply

Software Stack

Python

OpenCV

MediaPipe

Cvzone

Tkinter

NumPy

GPIOZero

Matplotlib

Academic Purpose

This repository supports the academic project titled:

“DrowsyCam: Driver Safety System with Eye Recognition and Drowsiness Detection”

Submitted in partial fulfillment of the requirements for the Bachelor of Science in Computer Engineering.
