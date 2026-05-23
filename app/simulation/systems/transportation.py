from __future__ import annotations

import math

import networkx as nx
import numpy as np

from app.simulation.world_state import WorldState, clamp, clamp_array


def update_transportation(state: WorldState) -> None:
    citizens = state.citizens
    district_count = len(state.districts)
    x = np.array([district.x for district in state.districts], dtype=np.float32)
    y = np.array([district.y for district in state.districts], dtype=np.float32)
    transit = np.array([district.transit_access for district in state.districts], dtype=np.float32)
    infra = np.array([district.infrastructure_quality for district in state.districts], dtype=np.float32)
    home = citizens.home_district
    work = citizens.work_district
    same_district = home == work

    distances = np.sqrt((x[home] - x[work]) ** 2 + (y[home] - y[work]) ** 2)
    local_transit = (transit[home] + transit[work]) / 2
    local_infra = (infra[home] + infra[work]) / 2
    base_commute = 10 + distances * (1.4 - local_transit * 0.48)

    flow = np.zeros(district_count, dtype=np.float64)
    np.add.at(flow, home, np.where(same_district, 0.18, 1.0))
    np.add.at(flow, work, np.where(same_district, 0.12, 0.65))
    resident_counts = np.bincount(home, minlength=district_count).astype(np.float64)
    pressure = flow / np.maximum(120.0, resident_counts * 0.62)

    graph = nx.Graph()
    graph.add_nodes_from(range(district_count))
    for road in state.roads:
        road_distance = math.dist((x[road.source], y[road.source]), (x[road.target], y[road.target]))
        graph.add_edge(road.source, road.target, weight=max(1.0, road_distance / max(0.25, road.capacity)))
    centrality = nx.betweenness_centrality(graph, weight="weight", normalized=True) if graph.number_of_edges() else {}

    for district in state.districts:
        district_pressure = pressure[district.id]
        centrality_load = centrality.get(district.id, 0.0) * 0.48
        transit_relief = district.transit_access * 0.32 + district.infrastructure_quality * 0.12
        target_congestion = clamp(district_pressure * 0.34 + centrality_load + district.density * 0.12 - transit_relief)
        district.congestion = clamp(
            district.congestion * 0.58
            + target_congestion * 0.42
            - state.government.infrastructure_budget * 0.018
        )
        district.commute_index = clamp(
            district.commute_index * 0.64
            + district.congestion * 0.18
            + (1 - district.infrastructure_quality) * 0.12
            + district.density * 0.055
            - district.transit_access * 0.05
        )

    congestion_by_home = np.array([state.districts[int(index)].congestion for index in home], dtype=np.float32)
    work_tech = np.array([state.districts[int(index)].tech_level for index in work], dtype=np.float32)
    remote_work = np.clip(work_tech * 0.32 + citizens.education * 0.2 - congestion_by_home * 0.12, 0, 0.48)
    remote_work = np.where(citizens.employed, remote_work, 0)
    commute_minutes = base_commute * (1 + congestion_by_home * 0.85) * (1.04 - local_infra * 0.2)
    commute_minutes *= 1 - remote_work * 0.34
    commute_minutes[same_district] *= 0.38
    commute_stress = np.clip((commute_minutes - 28) / 70, 0, 1)
    citizens.stress = clamp_array(citizens.stress * 0.91 + commute_stress * 0.055 - citizens.energy * 0.006)
    citizens.energy = clamp_array(citizens.energy + 0.02 - commute_stress * 0.034)
    citizens.productivity = clamp_array(
        citizens.productivity
        + (local_infra - 0.5) * 0.014
        - commute_stress * 0.023
        + remote_work * 0.012
    )

    for road in state.roads:
        local_flow = (pressure[road.source] + pressure[road.target]) / 2
        road.congestion = clamp(
            road.congestion * 0.62
            + local_flow * 0.24
            - road.capacity / 3600
            - state.government.infrastructure_budget * 0.012
        )

    state.metrics["commute_time"] = float(np.mean(commute_minutes))
    state.metrics["congestion"] = float(np.mean([district.congestion for district in state.districts]))
