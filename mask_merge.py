"""
MaskMerge - ComfyUI custom node
===============================

Merge several MASKs into ONE MASK before feeding a censor node.

Typical use: several detectors each emit their own masks; merging them first
means one single censor pass instead of stacking censor nodes on top of each
other (which double-censors pixels that were already covered).

What "merge" means when two masks overlap:

    union        : max()         -> pixel is masked if ANY input masks it
    intersection : min()         -> only pixels masked by EVERY input
    add          : sum, clamped  -> overlaps get denser / brighter
    average      : mean()        -> smooth blend of the inputs

Batch handling (batch_mode):

    flatten      : every frame of every input counts as a separate region and
                   they all collapse into ONE single-frame mask. This is what
                   you normally want - [3,H,W] + [2,H,W] + [1,H,W] -> [1,H,W].
    elementwise  : input A frame i merges with input B frame i.
                   Use for video, where each input carries the same frames.
"""

import torch
import torch.nn.functional as F

SLOT_LETTERS = "bcdefgh"


def _as_bhw(m):
    """Normalise an input to float32 [B, H, W] in 0..1."""
    if m is None:
        return None
    t = m.detach().to(torch.float32)
    while t.ndim > 3 and t.shape[-1] == 1:
        t = t[..., 0]
    if t.ndim > 3:
        t = t.reshape(-1, t.shape[-2], t.shape[-1])
    if t.ndim == 2:                      # [H, W] -> [1, H, W]
        t = t.unsqueeze(0)
    return torch.clamp(t, 0.0, 1.0)


def _resize(t, h, w):
    if t.shape[-2:] == (h, w):
        return t
    return F.interpolate(t.unsqueeze(1), size=(h, w), mode="bilinear",
                         align_corners=False).squeeze(1).clamp(0.0, 1.0)


def _pad_batch(t, b):
    """Align the frame count to b by repeating frames."""
    cur = t.shape[0]
    if cur == b:
        return t
    if cur == 1:
        return t.expand(b, -1, -1).contiguous()
    if cur < b:                          # repeat the last frame
        return torch.cat([t, t[-1:].expand(b - cur, -1, -1)], dim=0)
    return t[:b]


def _reduce(stack, operation):
    """stack: [N, H, W] -> [H, W]"""
    if operation == "union":
        return stack.max(dim=0).values
    if operation == "intersection":
        return stack.min(dim=0).values
    if operation == "add":
        return stack.sum(dim=0).clamp(0.0, 1.0)
    return stack.mean(dim=0)


class MaskMerge:
    """Combine multiple masks into one."""

    CATEGORY = "🧪AILab/▬BarCensor"
    RETURN_TYPES = ("MASK", "STRING")
    RETURN_NAMES = ("mask", "info")
    FUNCTION = "merge"

    @classmethod
    def INPUT_TYPES(cls):
        optional = {"mask_" + c: ("MASK",) for c in SLOT_LETTERS}
        optional["threshold"] = ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0,
                                           "step": 0.01})
        return {
            "required": {
                "mask_a": ("MASK",),
                "operation": (["union", "intersection", "add", "average"],),
                "batch_mode": (["flatten", "elementwise"],),
            },
            "optional": optional,
        }

    def merge(self, mask_a, operation, batch_mode, threshold=0.0, **rest):
        try:
            raw = [mask_a] + [rest.get("mask_" + c) for c in SLOT_LETTERS]
            masks = []
            for m in raw:
                t = _as_bhw(m)
                if t is not None and t.numel() > 0:
                    masks.append(t)

            if not masks:
                empty = torch.zeros((1, 1, 1), dtype=torch.float32)
                return (empty, "MaskMerge: no input mask")

            h = max(m.shape[-2] for m in masks)
            w = max(m.shape[-1] for m in masks)
            masks = [_resize(m, h, w) for m in masks]

            n_in = len(masks)
            frames = [m.shape[0] for m in masks]

            if batch_mode == "flatten":
                # every frame of every input is one region -> ONE output frame
                stack = torch.cat(masks, dim=0)                  # [N, H, W]
                out = _reduce(stack, operation).unsqueeze(0)     # [1, H, W]
            else:
                b = max(frames)
                stack = torch.stack([_pad_batch(m, b) for m in masks], dim=0)
                out = torch.stack([_reduce(stack[:, i], operation)
                                   for i in range(b)], dim=0)

            if threshold and threshold > 0.0:
                out = (out >= float(threshold)).to(torch.float32)

            out = out.clamp(0.0, 1.0).contiguous()
            cov = float(out.mean()) * 100.0 if out.numel() else 0.0
            info = ("merged {} mask inputs [{} / {}] | frames {} -> {} | "
                    "{}x{} | coverage {:.2f}%").format(
                n_in, operation, batch_mode, frames, out.shape[0], w, h, cov)
            return (out, info)

        except Exception:
            out = mask_a if isinstance(mask_a, torch.Tensor) else \
                torch.zeros((1, 1, 1), dtype=torch.float32)
            return (out, "MaskMerge: failed, passthrough")


NODE_CLASS_MAPPINGS = {
    "MaskMerge": MaskMerge,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MaskMerge": "Mask Merge (Combine Overlaps)",
}
