# Schematic Fort Mason map, walking routes and plain-language directions.
# Coordinates are on a 320x240 plan: the bay is north (top) and the Marina
# Blvd entrance is south (bottom). Positions are approximate.

import math

NAME = "Fort Mason"
KIND = "campus"
VIEW = (34, 34, 0.86, 0.95)  # source x, y and scale onto the map area

BUILDINGS = {
    "Festival Pavilion": (40, 40, 80, 60),
    "Gateway Pavilion": (150, 45, 70, 50),
    "Gateway Plaza": (225, 110, 50, 30),
    "Building C": (150, 110, 60, 22),
    "Building B": (150, 140, 60, 22),
    "Building A": (150, 170, 60, 22),
    "Firehouse": (90, 185, 35, 22),
    "Entrance": (140, 222, 80, 12),
}

# Order used by the "you are here" picker.
PLACES = ("Entrance", "Firehouse", "Building A", "Building B", "Building C",
          "Gateway Plaza", "Gateway Pavilion", "Festival Pavilion")

LABEL = {
    "Festival Pavilion": "Festival Pavilion",
    "Gateway Pavilion": "Gateway Pavilion",
    "Gateway Plaza": "Gateway Plaza",
    "Building C": "Bldg C",
    "Building B": "Bldg B",
    "Building A": "Bldg A",
    "Firehouse": "Firehouse",
    "Entrance": "Marina Blvd entrance",
}

MAP_LABEL = {
    "Festival Pavilion": ("Festival", "Pavilion"),
    "Gateway Pavilion": ("Gateway", "Pavilion"),
    "Gateway Plaza": ("Plaza",),
    "Building C": ("Bldg C",),
    "Building B": ("Bldg B",),
    "Building A": ("Bldg A",),
    "Firehouse": ("Fire", "house"),
    "Entrance": ("Entrance",),
}

ROOMS = {
    "Main Stage": "Festival Pavilion",
    "Silent Disco Demos": "Festival Pavilion",
    "Silent Disco Breakouts": "Festival Pavilion",
    "The Speakeasy": "Festival Pavilion",
    "Demos & Donuts": "Gateway Pavilion",
    "Cowell Theater": "Gateway Pavilion",
    "Workshops": "Gateway Pavilion",
    "Outdoor Theater": "Gateway Plaza",
    "Ship & Tell": "Firehouse",
    "BATS Theatre": "Building B",
    "Sandbox": "Building C",
}

FLOORS = {
    "Demos & Donuts": "Level 2",
    "Workshops": "Level 1",
    "BATS Theatre": "3rd Floor",
    "Sandbox": "3rd Floor, Founders Inc.",
    "The Speakeasy": "GitHub Central",
}

# Walkway graph. The main path runs north from the entrance between the
# Firehouse and Building A, past Buildings A, B and C, to the piers, then
# west to Festival Pavilion or east to Gateway Pavilion and the plaza.
NODES = {
    "ent": (160, 222),
    "s0": (137, 222),
    "sf": (137, 196),
    "sa": (137, 181),
    "sb": (137, 151),
    "sc": (137, 121),
    "j": (137, 104),
    "w1": (80, 104),
    "e1": (185, 104),
    "e2": (250, 104),
    "d_fest": (80, 100),
    "d_gate": (185, 95),
    "d_plaza": (250, 110),
    "d_fire": (125, 196),
    "d_a": (150, 181),
    "d_b": (150, 151),
    "d_c": (150, 121),
}

EDGES = (
    ("ent", "s0"), ("s0", "sf"), ("sf", "sa"), ("sa", "sb"), ("sb", "sc"),
    ("sc", "j"), ("j", "w1"), ("j", "e1"), ("e1", "e2"),
    ("w1", "d_fest"), ("e1", "d_gate"), ("e2", "d_plaza"),
    ("sf", "d_fire"), ("sa", "d_a"), ("sb", "d_b"), ("sc", "d_c"),
)

DOOR = {
    "Entrance": "ent",
    "Festival Pavilion": "d_fest",
    "Gateway Pavilion": "d_gate",
    "Gateway Plaza": "d_plaza",
    "Firehouse": "d_fire",
    "Building A": "d_a",
    "Building B": "d_b",
    "Building C": "d_c",
}

# A path node that sits beside a building, used for "walk past ..." text.
BESIDE = {"sf": "Firehouse", "sa": "Building A", "sb": "Building B",
          "sc": "Building C", "e1": "Gateway Pavilion"}

METRES_PER_UNIT = 1.8
WALK_METRES_PER_MIN = 80

_adjacent = {}
for _a, _b in EDGES:
    _adjacent.setdefault(_a, []).append(_b)
    _adjacent.setdefault(_b, []).append(_a)


def building_for(room, where):
    """The map building for a session, or None when it is off the map."""
    if room in ROOMS:
        return ROOMS[room]
    where = where or ""
    for name in ("Festival Pavilion", "Gateway Pavilion", "Gateway Plaza",
                 "Building A", "Building B", "Building C", "Firehouse"):
        if name in where:
            return name
    return None


def floor_for(room, where):
    if room in FLOORS:
        return FLOORS[room]
    if where and "," in where:
        return where.split(",", 1)[1].strip()
    return ""


def _distance(a, b):
    ax, ay = NODES[a]
    bx, by = NODES[b]
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)


def route(origin, target):
    """Shortest list of node names between two buildings' doors."""
    start, goal = DOOR[origin], DOOR[target]
    best = {start: 0}
    previous = {}
    todo = [start]
    while todo:
        todo.sort(key=lambda n: best[n])
        here = todo.pop(0)
        if here == goal:
            break
        for step in _adjacent[here]:
            cost = best[here] + _distance(here, step)
            if step not in best or cost < best[step]:
                best[step] = cost
                previous[step] = here
                todo.append(step)
    path = [goal]
    while path[-1] != start:
        path.append(previous[path[-1]])
    path.reverse()
    return path


def points(path):
    return [NODES[n] for n in path]


def length(path):
    total = 0
    for i in range(1, len(path)):
        total += _distance(path[i - 1], path[i])
    return total


def walk_minutes(path):
    return max(1, int(length(path) * METRES_PER_UNIT / WALK_METRES_PER_MIN + 0.5))


def _join_passed(names):
    """Bldg A, Bldg B, Bldg C -> Bldg A-C (in walking order)."""
    out = []
    run = []
    for name in names + [None]:
        if name and name.startswith("Building "):
            run.append(name[-1])
            continue
        if run:
            out.append("Bldg " + min(run) + ("-" + max(run) if len(run) > 1 else ""))
            run = []
        if name:
            out.append(LABEL[name])
    if len(out) > 1:
        return ", ".join(out[:-1]) + " & " + out[-1]
    return out[0] if out else ""


def directions(origin, target, floor=""):
    """Short steps that name the stops on the way. The map line shows the
    way, so nobody has to know which way they're facing."""
    room = (", " + floor) if floor else ""
    if origin == target:
        return ["You're here!", "Find " + (floor or "your room") + "."]
    path = route(origin, target)
    passed = [BESIDE[n] for n in path[1:-1]
              if n in BESIDE and BESIDE[n] not in (origin, target)]
    steps = []
    if passed:
        steps.append("Follow the green line past " + _join_passed(passed) + ".")
    else:
        steps.append("Follow the green line.")
    if target == "Entrance":
        steps.append("Leave by the Entrance.")
    else:
        steps.append("Go into " + LABEL[target] + room + ".")
    return steps
