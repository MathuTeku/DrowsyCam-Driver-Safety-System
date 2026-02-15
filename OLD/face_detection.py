import cv2
import dlib
import numpy as np
import math

# Load dlib's face detector and shape predictor
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

# Indices for left and right eye landmarks (from dlib's 68-point model)
# Left eye: 36, 37, 38, 39, 40, 41
# Right eye: 42, 43, 44, 45, 46, 47
LEFT_EYE_INDICES = list(range(36, 42))
RIGHT_EYE_INDICES = list(range(42, 48))

def calculate_distance(p1, p2):
    """Calculates Euclidean distance between two points."""
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

def ear_calculator(eye_points):
    """
    Calculates the Eye Aspect Ratio (EAR) for a given eye.
    Eye points should be in the order: P1, P2, P3, P4, P5, P6 (from dlib).
    """
    # Vertical distances
    A = calculate_distance(eye_points[1], eye_points[5]) # P2-P6
    B = calculate_distance(eye_points[2], eye_points[4]) # P3-P5
    # Horizontal distance
    C = calculate_distance(eye_points[0], eye_points[3]) # P1-P4

    # EAR calculation
    ear = (A + B) / (2.0 * C)
    return ear

def get_largest_face_landmarks(frame):
    """
    Detects faces in the frame and returns landmarks for the largest face.
    Returns None if no face is detected.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector(gray)

    if not faces:
        return None

    largest_face = None
    max_area = 0

    for face in faces:
        area = (face.right() - face.left()) * (face.bottom() - face.top())
        if area > max_area:
            max_area = area
            largest_face = face

    if largest_face:
        landmarks = predictor(gray, largest_face)
        # Convert dlib landmarks to a list of (x, y) tuples
        points = []
        for i in range(0, 68):
            points.append((landmarks.part(i).x, landmarks.part(i).y))
        return points
    return None

def draw_landmarks(frame, landmarks):
    """Draws facial landmarks on the frame for visualization."""
    for i, (x, y) in enumerate(landmarks):
        cv2.circle(frame, (x, y), 1, (0, 255, 0), -1) # Green circles for landmarks
        # Optionally draw lines for eyes
        if i in LEFT_EYE_INDICES or i in RIGHT_EYE_INDICES:
            cv2.circle(frame, (x, y), 2, (0, 0, 255), -1) # Red circles for eye landmarks
    return frame