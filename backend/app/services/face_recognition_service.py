"""
Face recognition service using the face_recognition library.

PRIVACY CONSIDERATIONS:
- Face embeddings (128-dimensional vectors) are stored instead of raw images
- Embeddings cannot be reverse-engineered back to the original face
- Consider implementing data retention policies
- Ensure users have consented to biometric data collection
"""

import io
import pickle
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List
from PIL import Image

import face_recognition

from app.config import get_settings
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger()


class FaceRecognitionService:
    def __init__(self):
        self.model = settings.FACE_DETECTION_MODEL
        self.threshold = settings.FACE_MATCH_THRESHOLD

    def detect_faces(self, image_data: bytes) -> Tuple[bool, int, str]:
        try:
            image = self._load_image(image_data)
            if image is None:
                return False, 0, "Failed to load image"

            face_locations = face_recognition.face_locations(image, model=self.model)
            num_faces = len(face_locations)

            if num_faces == 0:
                return False, 0, "No face detected in the image"
            elif num_faces > 1:
                return True, num_faces, f"Multiple faces detected ({num_faces}). Please use an image with only one face."

            return True, 1, "Face detected successfully"
        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return False, 0, f"Face detection failed: {str(e)}"

    def extract_embedding(self, image_data: bytes) -> Tuple[Optional[bytes], str]:
        try:
            image = self._load_image(image_data)
            if image is None:
                return None, "Failed to load image"

            face_locations = face_recognition.face_locations(image, model=self.model)
            if len(face_locations) == 0:
                return None, "No face detected"
            if len(face_locations) > 1:
                return None, "Multiple faces detected. Use image with single face."

            encodings = face_recognition.face_encodings(image, face_locations)
            if len(encodings) == 0:
                return None, "Could not extract face features"

            embedding = encodings[0]
            embedding_bytes = pickle.dumps(embedding)

            return embedding_bytes, "Embedding extracted successfully"
        except Exception as e:
            logger.error(f"Embedding extraction error: {e}")
            return None, f"Embedding extraction failed: {str(e)}"

    def compare_faces(
        self,
        probe_image_data: bytes,
        registered_embeddings: List[Tuple[str, str, str, bytes]]
    ) -> Tuple[Optional[str], Optional[str], Optional[str], float, str]:
        try:
            image = self._load_image(probe_image_data)
            if image is None:
                return None, None, None, 0.0, "Failed to load image"

            face_locations = face_recognition.face_locations(image, model=self.model)
            if len(face_locations) == 0:
                return None, None, None, 0.0, "No face detected"

            probe_encodings = face_recognition.face_encodings(image, face_locations)
            if len(probe_encodings) == 0:
                return None, None, None, 0.0, "Could not extract face features"

            probe_embedding = probe_encodings[0]

            best_match = None
            best_distance = float('inf')

            for user_id, employee_id, name, embedding_bytes in registered_embeddings:
                try:
                    stored_embedding = pickle.loads(embedding_bytes)
                    distance = face_recognition.face_distance([stored_embedding], probe_embedding)[0]

                    if distance < best_distance:
                        best_distance = distance
                        best_match = (user_id, employee_id, name)
                except Exception as e:
                    logger.warning(f"Error comparing with user {user_id}: {e}")
                    continue

            confidence = 1.0 - best_distance
            threshold = self.get_current_threshold()

            if best_match and best_distance < (1.0 - threshold):
                return (
                    best_match[0],
                    best_match[1],
                    best_match[2],
                    confidence,
                    "Face recognized"
                )
            else:
                return (
                    None,
                    None,
                    None,
                    confidence,
                    "Face not recognized (below confidence threshold)"
                )

        except Exception as e:
            logger.error(f"Face comparison error: {e}")
            return None, None, None, 0.0, f"Face comparison failed: {str(e)}"

    def get_current_threshold(self) -> float:
        return settings.FACE_MATCH_THRESHOLD

    def _load_image(self, image_data: bytes) -> Optional[np.ndarray]:
        try:
            image = Image.open(io.BytesIO(image_data))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            return np.array(image)
        except Exception as e:
            logger.error(f"Image loading error: {e}")
            return None

    def validate_image(self, image_data: bytes) -> Tuple[bool, str]:
        if not image_data:
            return False, "No image data provided"

        if len(image_data) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            return False, f"Image size exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit"

        try:
            image = Image.open(io.BytesIO(image_data))
            if image.width < 100 or image.height < 100:
                return False, "Image too small. Minimum size is 100x100 pixels."
            if image.width > 4000 or image.height > 4000:
                return False, "Image too large. Maximum size is 4000x4000 pixels."
            return True, "Image valid"
        except Exception as e:
            return False, f"Invalid image format: {str(e)}"


face_service = FaceRecognitionService()


def get_face_service() -> FaceRecognitionService:
    return face_service
