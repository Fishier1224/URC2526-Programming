import cv2
import numpy as np
import onnxruntime as ort

# -------------------- Config --------------------
MODEL_PATH      = "configs/models/best_fixed.onnx"
CAMERA_INDEX    = 0
CONF_THRESHOLD  = 0.25
IOU_THRESHOLD   = 0.45
INPUT_SIZE      = 640
CLASSES = ["ArUcoTag", "Bottle", "BrickHammer", "OrangeHammer"]

# -------------------- Load Model on GPU --------------------
session = ort.InferenceSession(
    MODEL_PATH,
    providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
)
input_name = session.get_inputs()[0].name
print("Running on:", session.get_providers()[0])

# -------------------- Open Camera --------------------
cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

def preprocess(frame):
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (INPUT_SIZE, INPUT_SIZE))
    img = img.astype(np.float32) / 255.0
    img = np.transpose(img, (2, 0, 1))[None]  # -> [1, 3, H, W]
    return np.ascontiguousarray(img)

def postprocess(output, orig_h, orig_w):
    preds = output[0].T  # [8400, 4+num_classes]
    boxes, scores = preds[:, :4], preds[:, 4:]
    class_ids   = np.argmax(scores, axis=1)
    confs       = scores[np.arange(len(scores)), class_ids]

    mask = confs > CONF_THRESHOLD
    boxes, confs, class_ids = boxes[mask], confs[mask], class_ids[mask]
    if len(boxes) == 0:
        return [], [], []

    sx, sy = orig_w / INPUT_SIZE, orig_h / INPUT_SIZE
    x1 = (boxes[:, 0] - boxes[:, 2] / 2) * sx
    y1 = (boxes[:, 1] - boxes[:, 3] / 2) * sy
    x2 = (boxes[:, 0] + boxes[:, 2] / 2) * sx
    y2 = (boxes[:, 1] + boxes[:, 3] / 2) * sy
    xyxy = np.stack([x1, y1, x2, y2], axis=1)

    idxs = cv2.dnn.NMSBoxes(xyxy.tolist(), confs.tolist(), CONF_THRESHOLD, IOU_THRESHOLD)
    idxs = idxs.flatten() if len(idxs) else []
    return xyxy[idxs], confs[idxs], class_ids[idxs]

# -------------------- Inference Loop --------------------
frame_count = 0
try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        orig_h, orig_w = frame.shape[:2]
        outputs = session.run(None, {input_name: preprocess(frame)})
        boxes, confs, class_ids = postprocess(outputs[0], orig_h, orig_w)

        for box, conf, cls_id in zip(boxes, confs, class_ids):
            x1, y1, x2, y2 = map(int, box)
            label = f"{CLASSES[cls_id]} {conf:.2f}"
            print(f"Frame {frame_count} - {label}")
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        frame_count += 1

except KeyboardInterrupt:
    print("Stopped by user")
finally:
    cap.release()
    print("Inference complete. Done.")
