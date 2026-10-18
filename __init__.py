from .barcensor import BarCensor
from .mask_merge import MaskMerge

NODE_CLASS_MAPPINGS = {
    "BarCensor": BarCensor,
    "MaskMerge": MaskMerge,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "BarCensor": "Bar Censor (Parallel Bars)",
    "MaskMerge": "Mask Merge (Combine Overlaps)",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS",
           "BarCensor", "MaskMerge"]
