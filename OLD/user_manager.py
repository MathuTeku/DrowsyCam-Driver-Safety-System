import os

USER_DATA_DIR = "." # Current directory

def save_user_data(username, eye_open_ref, eye_closed_ref):
    """Saves user's eye reference data to a text file."""
    filepath = os.path.join(USER_DATA_DIR, f"{username}.txt")
    try:
        with open(filepath, 'w') as f:
            f.write(f"eye_open_ref={eye_open_ref}\n")
            f.write(f"eye_closed_ref={eye_closed_ref}\n")
        print(f"User data saved for {username} at {filepath}")
    except IOError as e:
        print(f"Error saving user data for {username}: {e}")

def load_user_data(username):
    """Loads user's eye reference data from a text file."""
    filepath = os.path.join(USER_DATA_DIR, f"{username}.txt")
    eye_open_ref = None
    eye_closed_ref = None
    try:
        with open(filepath, 'r') as f:
            for line in f:
                if line.startswith("eye_open_ref="):
                    eye_open_ref = float(line.split('=')[1].strip())
                elif line.startswith("eye_closed_ref="):
                    eye_closed_ref = float(line.split('=')[1].strip())
        if eye_open_ref is None or eye_closed_ref is None:
            raise ValueError("Incomplete user data in file.")
        print(f"User data loaded for {username} from {filepath}")
        return eye_open_ref, eye_closed_ref
    except FileNotFoundError:
        raise FileNotFoundError(f"User data file not found for {username}.")
    except ValueError as e:
        raise ValueError(f"Invalid data format in {filepath}: {e}")
    except IOError as e:
        print(f"Error loading user data for {username}: {e}")
        raise

def list_users():
    """Scans the directory for user data files and returns a list of usernames."""
    users = []
    for filename in os.listdir(USER_DATA_DIR):
        if filename.endswith(".txt"):
            filepath = os.path.join(USER_DATA_DIR, filename)
            try:
                with open(filepath, 'r') as f:
                    # Check if it's a valid user data file by looking for key lines
                    content = f.read()
                    if "eye_open_ref=" in content and "eye_closed_ref=" in content:
                        username = filename[:-4] # Remove .txt extension
                        users.append(username)
            except Exception as e:
                print(f"Could not read {filename} as user data: {e}")
    return sorted(users)

# Example usage (for testing, not part of the main app flow)
if __name__ == "__main__":
    # Test saving
    save_user_data("test_user_1", 0.3, 0.1)
    save_user_data("test_user_2", 0.28, 0.09)

    # Test listing
    print("Available users:", list_users())

    # Test loading
    try:
        open_ref, closed_ref = load_user_data("test_user_1")
        print(f"Loaded test_user_1: Open={open_ref}, Closed={closed_ref}")
    except Exception as e:
        print(e)

    try:
        load_user_data("non_existent_user")
    except Exception as e:
        print(e)