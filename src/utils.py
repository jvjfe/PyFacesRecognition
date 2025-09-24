import os, pickle, cv2, face_recognition, numpy as np

faces_dir = "faces"
os.makedirs(faces_dir, exist_ok=True)
encodings_file = os.path.join(faces_dir, "encodings.pkl")
cards_file = os.path.join(faces_dir, "cards.pkl")

def load_known_faces():
    encodings, names = [], []
    if os.path.exists(encodings_file):
        with open(encodings_file, "rb") as f:
            data = pickle.load(f)
            raw_encodings = data.get("encodings", [])
            raw_names = data.get("names", [])
            for e, n in zip(raw_encodings, raw_names):
                arr = np.array(e)
                if arr.shape == (128,):
                    encodings.append(arr)
                    names.append(n)
    return encodings, names

def save_known_faces(encodings, names):
    serializable_encodings = [e.tolist() for e in encodings]
    with open(encodings_file, "wb") as f:
        pickle.dump({"encodings": serializable_encodings, "names": names}, f)

def get_face_encoding(image):
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_image, model="hog")
    if not face_locations:
        return None
    encodings = face_recognition.face_encodings(rgb_image, known_face_locations=face_locations)
    return encodings[0] if encodings else None

def compare_faces(known_encodings, known_names, encoding, tolerance=0.5):
    if not known_encodings or encoding is None:
        return None
    known_encodings = [np.array(e) for e in known_encodings if np.array(e).shape == (128,)]
    encoding = np.array(encoding)
    if encoding.shape != (128,) or not known_encodings:
        return None
    results = face_recognition.compare_faces(known_encodings, encoding, tolerance=tolerance)
    if any(results):
        index = results.index(True)
        return known_names[index]
    return None

def load_cards():
    if os.path.exists(cards_file):
        with open(cards_file, "rb") as f:
            return pickle.load(f)
    return {}

def save_cards(cards):
    with open(cards_file, "wb") as f:
        pickle.dump(cards, f)
