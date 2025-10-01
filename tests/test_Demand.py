"""Module to test the Demand class and its associated pa.DataFrameModel classes."""

import re

import pytest

from framcore.attributes import AvgFlowVolume, ElasticDemand, Elasticity, Price, ReservePrice
from framcore.components import Demand


def test_init_condition_reserve_price_and_elastic_demand() -> None:
    with pytest.raises(ValueError, match=re.escape("Cannot have 'reserve_price' and 'elastic_demand' at the same time.")):
        Demand(
            node="node",
            elastic_demand=ElasticDemand(
                price_elasticity=Elasticity(),
                min_price=Price(value=2.0, unit="NOK/MWh"),
                normal_price=Price(value=5.0, unit="NOK/MWh"),
                max_price=Price(value=10.0, unit="NOK/MWh"),
            ),
            reserve_price=ReservePrice(value=10.0, unit="NOK/MWh"),
        )

def test_init_default_consumption_is_avg_flow_volume() -> None:
    demand = Demand(node="node")
    assert isinstance(demand.get_consumption(), type(AvgFlowVolume()))
