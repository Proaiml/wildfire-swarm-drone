"""Bounded visibility-graph detours for the local simulation/pilot planner.
This is 2-D known-polygon planning, not terrain or onboard obstacle avoidance.
"""
import heapq
import math
from shapely.geometry import Point, LineString, box
from shapely.ops import transform
from core.geofence_manager import ZoneType


def plan_detour(geofence, start, goal, altitude, bounds=None):
    scale_y=111139.0
    scale_x=scale_y*math.cos(math.radians(start[0]))
    def xy(lat,lon): return ((lon-start[1])*scale_x,(lat-start[0])*scale_y)
    blockers=[]
    vertices=[]
    for zone in list(geofence.zones.values()):
        if zone.zone_type == ZoneType.HIGH_RISK_SEARCH or not zone.min_alt <= altitude <= zone.max_alt:
            continue
        local=transform(lambda x,y,z=None: ((x-start[1])*scale_x,(y-start[0])*scale_y),zone.polygon)
        blockers.append(local.buffer(zone.safety_margin_meters+1,join_style=2))
        outer=local.buffer(zone.safety_margin_meters+12,join_style=2).simplify(2,preserve_topology=True)
        vertices.extend(list(outer.exterior.coords)[:-1])
    area=None
    if bounds:
        left,bottom=xy(bounds['min_lat'],bounds['min_lon'])
        right,top=xy(bounds['max_lat'],bounds['max_lon'])
        area=box(left,bottom,right,top)
    nodes=[(0.,0.),xy(*goal)]+[p for p in vertices if area is None or area.covers(Point(p))]
    # Bound pathological user polygons; hold rather than block the control thread.
    if len(nodes)>130 or any(poly.covers(Point(nodes[0])) or poly.covers(Point(nodes[1])) for poly in blockers):
        return []
    def visible(a,b):
        line=LineString([a,b])
        return (area is None or area.covers(line)) and not any(poly.intersects(line) for poly in blockers)
    if visible(nodes[0],nodes[1]): return [goal]
    distance={0:0.};parent={};queue=[(0.,0)]
    while queue:
        cost,i=heapq.heappop(queue)
        if cost!=distance.get(i):continue
        if i==1:
            path=[]
            while i:
                x,y=nodes[i];path.append((start[0]+y/scale_y,start[1]+x/scale_x));i=parent[i]
            return list(reversed(path))
        for j,node in enumerate(nodes):
            if j==i or not visible(nodes[i],node):continue
            candidate=cost+math.dist(nodes[i],node)
            if candidate<distance.get(j,float('inf')):
                distance[j]=candidate;parent[j]=i;heapq.heappush(queue,(candidate,j))
    return []
