# fix_onnx.py
import onnx

model = onnx.load("configs/models/best.onnx")
print("Current IR version:", model.ir_version)
model.ir_version = 8  # downgrade to safe version
onnx.save(model, "configs/models/best_fixed.onnx")
print("Saved fixed model")
