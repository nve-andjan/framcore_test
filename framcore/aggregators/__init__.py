# framcore/aggregators/__init__.py
from framcore.aggregators.Aggregator import Aggregator
from framcore.aggregators.HydroAggregator import HydroAggregator
from framcore.aggregators.NodeAggregator import NodeAggregator
from framcore.aggregators.WindSolarAggregator import WindAggregator, SolarAggregator

__all__ = [
    "Aggregator",
    "HydroAggregator",
    "NodeAggregator",
    "SolarAggregator",
    "WindAggregator",
]
