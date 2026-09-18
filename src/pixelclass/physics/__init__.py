"""物理层：刚体、瓦片刚体组、集合容器（spec 03）。"""

from .body import BODY_TYPES, SHAPE_KINDS, Body, resolve_body_type
from .groups import BodiesGroup, TiledMapBodiesGroup
from .tiles import TiledMapBodies

__all__ = [
    "Body",
    "BodiesGroup",
    "TiledMapBodies",
    "TiledMapBodiesGroup",
    "BODY_TYPES",
    "SHAPE_KINDS",
    "resolve_body_type",
]
