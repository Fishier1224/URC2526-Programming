import os
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject

# ------------------------- Configs -------------------------
VIDEO_PATH = os.path.abspath("input_videos/IMG_1573.mp4")
OUTPUT_VIDEO_PATH = os.path.abspath("output_videos/output.mp4")
DEEPSTREAM_CONFIG = os.path.abspath("configs/yolo_config.txt")

os.makedirs(os.path.dirname(OUTPUT_VIDEO_PATH), exist_ok=True)

# ------------------------- Initialize -------------------------
Gst.init(None)
pipeline = Gst.Pipeline.new("ds-pipeline")

# Source
source = Gst.ElementFactory.make("filesrc", "file-source")
source.set_property("location", VIDEO_PATH)

demux = Gst.ElementFactory.make("qtdemux", "demux")

decoder = Gst.ElementFactory.make("nvv4l2decoder", "decoder")

streammux = Gst.ElementFactory.make("nvstreammux", "stream-muxer")
streammux.set_property("batch-size", 1)
streammux.set_property("width", 640)
streammux.set_property("height", 480)
streammux.set_property("batched-push-timeout", 4000000)

pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
pgie.set_property("config-file-path", DEEPSTREAM_CONFIG)

nvdsosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")

nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")

encoder = Gst.ElementFactory.make("nvv4l2h264enc", "h264-encoder")
encoder.set_property("bitrate", 4000000)

h264parse = Gst.ElementFactory.make("h264parse", "h264-parser")

mux = Gst.ElementFactory.make("qtmux", "mp4-muxer")

sink = Gst.ElementFactory.make("filesink", "file-sink")
sink.set_property("location", OUTPUT_VIDEO_PATH)
sink.set_property("sync", False)

# Add elements
for elem in [source, demux, decoder, streammux, pgie,
             nvdsosd, nvvidconv, encoder,
             h264parse, mux, sink]:
    if not elem:
        raise Exception("Failed to create element")
    pipeline.add(elem)

# Link file source
source.link(demux)

def on_pad_added(demux, pad):
    pad.link(decoder.get_static_pad("sink"))

demux.connect("pad-added", on_pad_added)

# Link decoder to streammux (special linking)
sinkpad = streammux.get_request_pad("sink_0")
srcpad = decoder.get_static_pad("src")
srcpad.link(sinkpad)

# Link rest
streammux.link(pgie)
pgie.link(nvdsosd)
nvdsosd.link(nvvidconv)
nvvidconv.link(encoder)
encoder.link(h264parse)
h264parse.link(mux)
mux.link(sink)

# Run
pipeline.set_state(Gst.State.PLAYING)

try:
    loop = GObject.MainLoop()
    loop.run()
except KeyboardInterrupt:
    pass
finally:
    pipeline.set_state(Gst.State.NULL)
    print(f"Done! Output saved to {OUTPUT_VIDEO_PATH}")
