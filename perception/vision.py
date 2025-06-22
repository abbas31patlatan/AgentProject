# File: perception/vision.py

import cv2
import numpy as np
import d3dshot
from typing import Any, Optional, List, Dict
from ultralytics import YOLO

class VisionPerceptor:
    """
    Gerçek zamanlı ekran/kamera görüntüsü alır, nesne tespiti yapar ve sahne özetler.
    YOLO ve diğer modellerle entegre çalışır.
    """

    def __init__(self, yolo_model_path: str = "models/gguf/yolov8n.pt"):
        self.d3d = d3dshot.create(capture_output="numpy")
        self.yolo = YOLO(yolo_model_path)
        self.cam = None  # opsiyonel kamera desteği

    def screenshot(self, region: Optional[tuple] = None) -> np.ndarray:
        """
        Ekran görüntüsü alır. (region: x, y, w, h opsiyonel)
        """
        img = self.d3d.screenshot(region=region)
        if img is None:
            raise RuntimeError("Ekran görüntüsü alınamadı!")
        return img

    def camera_frame(self, camera_id: int = 0) -> Optional[np.ndarray]:
        """
        Kameradan bir kare alır (varsayılan: 0. webcam).
        """
        if self.cam is None:
            self.cam = cv2.VideoCapture(camera_id)
        ret, frame = self.cam.read()
        return frame if ret else None

    def detect_objects(self, img: np.ndarray, conf: float = 0.25) -> List[Dict[str, Any]]:
        """
        YOLO ile nesne tespiti yapar.
        """
        results = self.yolo(img, conf=conf)
        detected = []
        for r in results:
            for box in r.boxes:
                detected.append({
                    "class": r.names[box.cls[0]],
                    "confidence": float(box.conf[0]),
                    "bbox": [int(x) for x in box.xyxy[0].tolist()],
                })
        return detected

    def annotate_image(self, img: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        """
        Bulunan nesneleri img üzerinde kutu+etiketle gösterir.
        """
        for obj in detections:
            x1, y1, x2, y2 = obj["bbox"]
            label = f"{obj['class']}:{obj['confidence']:.2f}"
            cv2.rectangle(img, (x1, y1), (x2, y2), (0,255,0), 2)
            cv2.putText(img, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
        return img

    def scene_summary(self, detections: List[Dict[str, Any]]) -> str:
        """
        Sahnenin kısa özetini verir (örnek: “2 insan, 1 kedi tespit edildi.”)
        """
        from collections import Counter
        counter = Counter(obj["class"] for obj in detections)
        summary = ", ".join([f"{v} {k}" for k, v in counter.items()])
        return f"Tespitler: {summary}" if summary else "Hiçbir nesne bulunamadı."
