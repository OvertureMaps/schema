"""
Overture GERS Examples Package

This package provides examples for working with GERS (Global Entity Reference System) 
in Overture Maps data, including GPS trace matching to road segments.
"""

__version__ = "0.1.0"

from .match_traces import main as match_traces_main
from .match_classes import (
    TraceSnapOptions,
    MatchableFeature, 
    TraceMatchResult,
    SnappedPointPrediction,
    PointSnapInfo,
    RouteStep
)

__all__ = [
    "match_traces_main",
    "TraceSnapOptions",
    "MatchableFeature",
    "TraceMatchResult", 
    "SnappedPointPrediction",
    "PointSnapInfo",
    "RouteStep"
]