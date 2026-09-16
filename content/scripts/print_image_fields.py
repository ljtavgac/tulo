"""Reads a /pages/{slug} JSON response from stdin and prints its
image_url + image_attribution as compact JSON on one line, prefixed with
the slug -- used to read back a page's real, already-selected image data
from a live environment (e.g. prod) without embedding multi-line Python
directly in a workflow's YAML."""

import json
import sys

data = json.load(sys.stdin)
content = data.get("content", {})
print(json.dumps({
    "slug": data.get("slug"),
    "image_url": content.get("image_url"),
    "image_attribution": content.get("image_attribution"),
}))
