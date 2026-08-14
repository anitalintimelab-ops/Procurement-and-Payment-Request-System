import base64
import os
from dataclasses import dataclass

import streamlit.components.v1 as components


_COMPONENT = components.declare_component(
    "timelab_mobile_camera",
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "mobile_camera_component"),
)


@dataclass
class MobileCameraUpload:
    name: str
    mime_type: str
    data: bytes

    def getvalue(self):
        return self.data


def mobile_camera_input(label, key):
    value = _COMPONENT(label=label, key=key, default=None)
    if not isinstance(value, dict) or not value.get("data"):
        return None
    try:
        return MobileCameraUpload(
            name=value.get("name") or "camera.jpg",
            mime_type=value.get("mime_type") or "image/jpeg",
            data=base64.b64decode(value["data"]),
        )
    except Exception:
        return None
