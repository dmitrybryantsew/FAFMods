#!/usr/bin/env python3
"""
Test Suite & Verification Tool for Raptor Hive Cliff / Hill / Mountain Detection
and Air-Only Production System.

This script tests and verifies:
1. Local terrain slope calculation (steep cliff slopes)
2. Radial cliff encirclement raycasting (mountain summits, mesas, plateaus)
3. Navigation connectivity checking (isolated plateaus, unpathable terrain)
4. Runtime land unit stacking watchdog
5. Air-only unit roster composition and distribution across Tech Anger tiers
"""

import math
import sys

# Constants matching FAF Moho Engine & RaptorSpawner.lua
MAX_LAND_SLOPE = 0.50          # Standard FAF land unit slope traversal limit
CLIFF_SLOPE_THRESHOLD = 0.65   # Slope threshold above which terrain is impassable cliff
LOCAL_SLOPE_THRESHOLD = 0.45   # Local slope directly under/around hive
NUM_RADIAL_RAYS = 8            # Radial directions sampled
RAY_DISTANCE = 28.0            # Distance to trace outward
STEP_SIZE = 4.0                # Step increment per ray
BLOCKED_RAY_THRESHOLD = 6      # >= 6 of 8 rays (75%+) blocked -> Encircled
MOUNTAIN_DROP_THRESHOLD = 6.0  # Average elevation drop indicating elevated peak

# Air unit roster matching RaptorFaction
AIR_ROSTER_T1 = ['XRA0115', 'XRA0104', 'XRA0111']
AIR_ROSTER_T2 = [
    'XRA0205', 'XRA0204', 'XRA0213', 'XRA0216', 'XRA0218',
    'XRA0219', 'XRA0224', 'XRA0227', 'XRA0115', 'XRA0104', 'XRA0111'
]
AIR_ROSTER_T3 = [
    'XRA0314', 'XRA0227', 'XRA0205', 'XRA0216', 'XRA0224',
    'XRA0204', 'XRA0314', 'XRA0115', 'XRA0111'
]
LAND_UNITS = [
    'XRA0100', 'XRA0101', 'XRA0103', 'XRA0109', 'XRA0116',
    'XRA0201', 'XRA0202', 'XRA0203', 'XRA0206', 'XRA0225',
    'XRA0301', 'XRA0302', 'XRA0303', 'XRA0310', 'XRA0328'
]

class MockTerrain:
    """Mock heightmap provider for synthetic test cases."""
    def __init__(self, mode='flat', **kwargs):
        self.mode = mode
        self.kwargs = kwargs

    def get_height(self, x, z):
        if self.mode == 'flat':
            return 20.0
        elif self.mode == 'steep_slope':
            # Uniform steep incline: height increases by 0.55 per unit along X
            return 20.0 + x * 0.55
        elif self.mode == 'mountain_peak':
            # High plateau in center (r <= 6), dropping steeply into a cliff (r > 6)
            cx = self.kwargs.get('cx', 100.0)
            cz = self.kwargs.get('cz', 100.0)
            dist = math.hypot(x - cx, z - cz)
            if dist <= 6.0:
                return 50.0
            elif dist <= 14.0:
                # Steep cliff drop from 50 down to 20 over 8 units (slope = 30/8 = 3.75)
                return 50.0 - (dist - 6.0) * 3.75
            else:
                return 20.0
        elif self.mode == 'gentle_hill':
            # Gentle rolling hill: elevated by 8 units at center, slope 0.20 in all directions (no cliffs)
            cx = self.kwargs.get('cx', 100.0)
            cz = self.kwargs.get('cz', 100.0)
            dist = math.hypot(x - cx, z - cz)
            if dist <= 5.0:
                return 28.0
            return max(20.0, 28.0 - (dist - 5.0) * 0.20)

    def is_blocking(self, x, z):
        return False


class MockNavMesh:
    """Mock navigation mesh provider."""
    def __init__(self, can_path=True, label=1, area=10.0):
        self._can_path = can_path
        self._label = label
        self._area = area

    def is_generated(self):
        return True

    def get_label(self, layer, pos):
        if layer == 'Land':
            return self._label
        return 1

    def get_label_metadata(self, label):
        return {'Area': self._area}

    def can_path_to(self, layer, origin, destination):
        if layer == 'Land':
            return self._can_path
        return True


def evaluate_hive_terrain(pos, terrain, nav_mesh=None, enemy_positions=None, nearby_land_units=None):
    """
    Python implementation of IsHiveOnCliffOrHill from RaptorSpawner.lua.
    Evaluates:
    - Stacking watchdog
    - Nav mesh connectivity & unpathable terrain
    - Local terrain slope
    - Radial cliff encirclement & mountain peak detection
    """
    hx, hy, hz = pos[0], pos[1], pos[2]

    # Layer 1: Stacking Watchdog (Active land units stuck near hive)
    if nearby_land_units is not None:
        stuck_count = sum(1 for u in nearby_land_units if u.get('idle_time', 0) > 25)
        if stuck_count >= 4:
            return True, 'LandUnitsStacked', {'stuck_count': stuck_count}

    # Layer 2: NavMesh Connectivity (Macro pathing)
    if nav_mesh and nav_mesh.is_generated():
        hive_label = nav_mesh.get_label('Land', pos)
        if hive_label is None or hive_label == -1:
            return True, 'UnpathableTerrain', {'label': hive_label}

        meta = nav_mesh.get_label_metadata(hive_label)
        if meta and meta.get('Area', 999) < 0.05:
            return True, 'IsolatedSmallPlateau', {'area': meta.get('Area')}

        if enemy_positions:
            can_reach_any = any(nav_mesh.can_path_to('Land', pos, dest) for dest in enemy_positions)
            if not can_reach_any:
                return True, 'NoLandPathToEnemy', {'dest_count': len(enemy_positions)}

    # Layer 3: Local Slope Gradient
    h_center = terrain.get_height(hx, hz)
    test_dist = 5.0
    h_n = terrain.get_height(hx, hz + test_dist)
    h_s = terrain.get_height(hx, hz - test_dist)
    h_e = terrain.get_height(hx + test_dist, hz)
    h_w = terrain.get_height(hx - test_dist, hz)

    max_local_slope = max(
        abs(h_n - h_center) / test_dist,
        abs(h_s - h_center) / test_dist,
        abs(h_e - h_center) / test_dist,
        abs(h_w - h_center) / test_dist,
    )

    if max_local_slope >= LOCAL_SLOPE_THRESHOLD:
        return True, 'SteepCliffSlope', {'max_local_slope': max_local_slope}

    # Layer 4: Radial Cliff Perimeter Raycasting
    blocked_directions = 0
    total_height_drop = 0.0

    for i in range(NUM_RADIAL_RAYS):
        angle = i * (2.0 * math.pi / NUM_RADIAL_RAYS)
        dir_x = math.cos(angle)
        dir_z = math.sin(angle)
        ray_blocked = False
        prev_h = h_center

        dist = STEP_SIZE
        while dist <= RAY_DISTANCE:
            rx = hx + dir_x * dist
            rz = hz + dir_z * dist
            cur_h = terrain.get_height(rx, rz)
            step_slope = abs(cur_h - prev_h) / STEP_SIZE

            if step_slope >= CLIFF_SLOPE_THRESHOLD or terrain.is_blocking(rx, rz):
                ray_blocked = True
                break

            prev_h = cur_h
            dist += STEP_SIZE

        edge_h = terrain.get_height(hx + dir_x * RAY_DISTANCE, hz + dir_z * RAY_DISTANCE)
        total_height_drop += (h_center - edge_h)

        if ray_blocked:
            blocked_directions += 1

    avg_drop = total_height_drop / NUM_RADIAL_RAYS

    if blocked_directions >= BLOCKED_RAY_THRESHOLD:
        return True, 'RadialCliffEncirclement', {
            'blocked_rays': blocked_directions,
            'avg_drop': avg_drop
        }

    if avg_drop >= MOUNTAIN_DROP_THRESHOLD and blocked_directions >= 4:
        return True, 'MountainPeakSummit', {
            'blocked_rays': blocked_directions,
            'avg_drop': avg_drop
        }

    return False, 'PathableTerrain', {
        'max_local_slope': max_local_slope,
        'blocked_rays': blocked_directions,
        'avg_drop': avg_drop
    }


def get_air_unit_pool(tech_anger, threat_profile):
    """Constructs the Air-Only unit pool based on Tech Anger and threat profile."""
    if tech_anger > 60:
        base = list(AIR_ROSTER_T3)
    elif tech_anger > 25:
        base = list(AIR_ROSTER_T2)
    else:
        base = list(AIR_ROSTER_T1)

    pool = list(base)
    if threat_profile.get('AirThreat'):
        pool.extend(['XRA0115', 'XRA0219', 'XRA0314'])
    if threat_profile.get('TurtleThreat'):
        pool.extend(['XRA0224', 'XRA0204', 'XRA0227'])
    if threat_profile.get('ExpThreat'):
        pool.extend(['XRA0216', 'XRA0205', 'XRA0314'])

    return pool


def run_tests():
    print("=" * 70)
    print("RUNNING RAPTOR HIVE CLIFF / HILL / MOUNTAIN DETECTION TEST SUITE")
    print("=" * 70)

    tests_passed = 0
    total_tests = 7

    # Test 1: Flat Valley Terrain (Should NOT be cliff-bound)
    terrain_flat = MockTerrain('flat')
    nav_flat = MockNavMesh(can_path=True, label=1, area=20.0)
    is_cliff, reason, details = evaluate_hive_terrain(
        [100.0, 20.0, 100.0],
        terrain_flat,
        nav_flat,
        enemy_positions=[[200.0, 20.0, 200.0]]
    )
    assert not is_cliff, f"Flat terrain should be pathable! Got {reason}"
    print("[PASS] Test 1: Flat valley terrain correctly identified as Pathable (Normal Hive)")
    tests_passed += 1

    # Test 2: Steep Cliff Slope (Hive placed on a steep mountainside, slope = 0.55)
    terrain_steep = MockTerrain('steep_slope')
    is_cliff, reason, details = evaluate_hive_terrain(
        [100.0, 75.0, 100.0],
        terrain_steep,
        nav_flat,
        enemy_positions=[[200.0, 20.0, 200.0]]
    )
    assert is_cliff and reason == 'SteepCliffSlope', f"Expected SteepCliffSlope, got {reason}"
    print(f"[PASS] Test 2: Steep mountainside slope detected ({reason}, slope={details['max_local_slope']:.2f}) -> AIR-ONLY")
    tests_passed += 1

    # Test 3: Mountain Peak / Mesa / Plateau (Surrounded by cliffs on all sides)
    terrain_mountain = MockTerrain('mountain_peak', cx=100.0, cz=100.0)
    is_cliff, reason, details = evaluate_hive_terrain(
        [100.0, 50.0, 100.0],
        terrain_mountain,
        nav_flat,
        enemy_positions=[[250.0, 20.0, 250.0]]
    )
    assert is_cliff and ('Cliff' in reason or 'Mountain' in reason), f"Expected cliff encirclement, got {reason}"
    print(f"[PASS] Test 3: Mountain peak surrounded by cliffs detected ({reason}, blocked={details['blocked_rays']}/8) -> AIR-ONLY")
    tests_passed += 1

    # Test 4: Gentle Rolling Hill (Slope 0.20, no cliffs -> normal land units can traverse)
    terrain_gentle = MockTerrain('gentle_hill', cx=100.0, cz=100.0)
    is_cliff, reason, details = evaluate_hive_terrain(
        [100.0, 28.0, 100.0],
        terrain_gentle,
        nav_flat,
        enemy_positions=[[250.0, 20.0, 100.0]]
    )
    assert not is_cliff, f"Gentle rolling hill should allow ground units! Got {reason}"
    print(f"[PASS] Test 4: Gentle rolling hill without cliffs correctly allows Normal production (blocked={details['blocked_rays']}/8)")
    tests_passed += 1

    # Test 5: Isolated Plateau / Island (NavMesh disconnected from enemy)
    nav_disconnected = MockNavMesh(can_path=False, label=5, area=2.0)
    is_cliff, reason, details = evaluate_hive_terrain(
        [100.0, 20.0, 100.0],
        terrain_flat,
        nav_disconnected,
        enemy_positions=[[300.0, 20.0, 300.0]]
    )
    assert is_cliff and reason == 'NoLandPathToEnemy', f"Expected NoLandPathToEnemy, got {reason}"
    print(f"[PASS] Test 5: Disconnected plateau/island with no path to enemy detected ({reason}) -> AIR-ONLY")
    tests_passed += 1

    # Test 6: Land Unit Stacking Watchdog (Previously spawned units stuck near hive)
    stuck_units = [
        {'id': 1, 'idle_time': 35},
        {'id': 2, 'idle_time': 30},
        {'id': 3, 'idle_time': 40},
        {'id': 4, 'idle_time': 28},
    ]
    is_cliff, reason, details = evaluate_hive_terrain(
        [100.0, 20.0, 100.0],
        terrain_flat,
        nav_flat,
        nearby_land_units=stuck_units
    )
    assert is_cliff and reason == 'LandUnitsStacked', f"Expected LandUnitsStacked, got {reason}"
    print(f"[PASS] Test 6: Runtime stacking watchdog successfully caught stuck land units ({reason}, count={details['stuck_count']}) -> AIR-ONLY")
    tests_passed += 1

    # Test 7: Air-Only Roster Composition (Ensures 0 land units exist in pool across tiers)
    for anger, label in [(10, "T1"), (40, "T2"), (80, "T3")]:
        pool = get_air_unit_pool(anger, {'TurtleThreat': True, 'AirThreat': True})
        land_in_pool = [u for u in pool if u in LAND_UNITS]
        assert len(land_in_pool) == 0, f"Found land units in air-only pool: {land_in_pool}"
        assert len(pool) > 0, "Air pool should not be empty!"
        print(f"[PASS] Test 7.{label}: Air-only roster for {label} (Anger={anger}) contains 100% aerial units (count={len(pool)}, land=0)")
    tests_passed += 1

    print("=" * 70)
    print(f"ALL TESTS PASSED: {tests_passed}/{total_tests} verification checks successful!")
    print("=" * 70)


if __name__ == '__main__':
    run_tests()
