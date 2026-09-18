from ultralytics import YOLO
import cv2


model = YOLO("best.pt")




image = cv2.imread("mana.jpg")
results = model(image)

for box in results[0].boxes:
    class_id = int(box.cls[0])
    confidence = float(box.conf[0])

    class_name = results[0].names[class_id]

    print("Tespit:", class_name)
    print("Güven:", confidence)