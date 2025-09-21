import heapq
import math
import time
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict

class AStarDijkstra:
    """
    Advanced pathfinding με A* και βελτιωμένο Dijkstra
    Συνδυάζει την ακρίβεια του Dijkstra με την ταχύτητα του A*
    """
    
    def __init__(self):
        self.nodes = {}  # node_id -> (lat, lon)
        self.graph = defaultdict(list)  # adjacency list
        self.performance_stats = {
            'total_searches': 0,
            'astar_searches': 0,
            'dijkstra_searches': 0,
            'avg_astar_time': 0,
            'avg_dijkstra_time': 0,
            'nodes_explored_astar': 0,
            'nodes_explored_dijkstra': 0
        }
        
    def haversine(self, lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """Υπολογισμός απόστασης Haversine σε χιλιόμετρα"""
        R = 6371  # Ακτίνα Γης σε km
        
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def manhattan_distance(self, node1: int, node2: int) -> float:
        """Manhattan distance heuristic (ταχύτερο από Haversine)"""
        if node1 not in self.nodes or node2 not in self.nodes:
            return 0
            
        lat1, lon1 = self.nodes[node1]
        lat2, lon2 = self.nodes[node2]
        
        # Προσεγγιστικό Manhattan distance σε km
        lat_diff = abs(lat2 - lat1) * 111  # 1 degree ≈ 111 km
        lon_diff = abs(lon2 - lon1) * 111 * math.cos(math.radians((lat1 + lat2) / 2))
        
        return lat_diff + lon_diff
    
    def euclidean_heuristic(self, node1: int, node2: int) -> float:
        """Euclidean distance heuristic (πιο ακριβής)"""
        if node1 not in self.nodes or node2 not in self.nodes:
            return 0
            
        lat1, lon1 = self.nodes[node1]
        lat2, lon2 = self.nodes[node2]
        
        return self.haversine(lon1, lat1, lon2, lat2)
    
    def adaptive_heuristic(self, node1: int, node2: int, distance_threshold: float = 10) -> float:
        """Προσαρμοστικό heuristic βάσει απόστασης"""
        if node1 not in self.nodes or node2 not in self.nodes:
            return 0
            
        # Για μικρές αποστάσεις χρησιμοποιούμε Manhattan (ταχύτερο)
        # Για μεγάλες αποστάσεις χρησιμοποιούμε Euclidean (ακριβέστερο)
        euclidean_dist = self.euclidean_heuristic(node1, node2)
        
        if euclidean_dist < distance_threshold:
            return self.manhattan_distance(node1, node2)
        else:
            return euclidean_dist
    
    def a_star_search(self, start: int, end: int, heuristic_type: str = 'adaptive') -> Optional[Tuple]:
        """
        A* αλγόριθμος με επιλογή heuristic
        
        Args:
            start: Κόμβος αφετηρίας
            end: Κόμβος προορισμού  
            heuristic_type: 'manhattan', 'euclidean', 'adaptive'
        """
        start_time = time.time()
        
        # Επιλογή heuristic function
        if heuristic_type == 'manhattan':
            heuristic = self.manhattan_distance
        elif heuristic_type == 'euclidean':
            heuristic = self.euclidean_heuristic
        else:  # adaptive
            heuristic = self.adaptive_heuristic
        
        # A* data structures
        open_set = [(0, start)]  # (f_score, node)
        came_from = {}
        g_score = {start: 0}  # Κόστος από start
        f_score = {start: heuristic(start, end)}  # g + h
        
        open_set_hash = {start}  # Για γρήγορο lookup
        closed_set = set()
        nodes_explored = 0
        
        print(f"🧠 A* search: {start} → {end} (heuristic: {heuristic_type})")
        
        while open_set:
            current_f, current = heapq.heappop(open_set)
            open_set_hash.discard(current)
            
            if current == end:
                # Βρήκαμε τον προορισμό!
                search_time = time.time() - start_time
                self._update_astar_stats(search_time, nodes_explored)
                
                print(f"✅ A* completed: {nodes_explored} nodes, {search_time:.3f}s")
                return self._reconstruct_astar_path(came_from, start, end)
            
            closed_set.add(current)
            nodes_explored += 1
            
            # Όριο για αποφυγή infinite loops
            if nodes_explored > 100000:
                print("⚠️ A* reached node limit")
                break
            
            # Εξερεύνηση γειτόνων
            for edge_data in self.graph.get(current, []):
                if len(edge_data) >= 3:
                    neighbor, distance, time_cost = edge_data[:3]
                else:
                    continue
                
                if neighbor in closed_set:
                    continue
                
                # Υπολογισμός g_score για αυτή τη διαδρομή
                tentative_g = g_score[current] + time_cost  # Χρησιμοποιούμε χρόνο ως κόστος
                
                if neighbor not in g_score:
                    g_score[neighbor] = float('inf')
                
                if tentative_g < g_score[neighbor]:
                    # Βρήκαμε καλύτερη διαδρομή
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + heuristic(neighbor, end)
                    
                    if neighbor not in open_set_hash:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
                        open_set_hash.add(neighbor)
        
        print("❌ A* failed to find path")
        return None
    
    def compare_algorithms(self, start: int, end: int) -> Dict:
        """Σύγκριση A* vs Dijkstra για benchmark"""
        print(f"\n🏁 Algorithm Comparison: {start} → {end}")
        
        results = {
            'start': start,
            'end': end,
            'algorithms': {}
        }
        
        # Test A* με διαφορετικά heuristics
        for heuristic in ['manhattan', 'euclidean', 'adaptive']:
            print(f"\n🧠 Testing A* with {heuristic} heuristic...")
            start_time = time.time()
            
            result = self.a_star_search(start, end, heuristic)
            
            if result:
                coords, total_dist, total_time, instructions = result
                search_time = time.time() - start_time
                
                results['algorithms'][f'astar_{heuristic}'] = {
                    'success': True,
                    'search_time': search_time,
                    'route_distance': total_dist,
                    'route_time': total_time,
                    'coordinates_count': len(coords),
                    'heuristic': heuristic
                }
            else:
                results['algorithms'][f'astar_{heuristic}'] = {
                    'success': False,
                    'search_time': time.time() - start_time,
                    'heuristic': heuristic
                }
        
        return results
    
    def _reconstruct_astar_path(self, came_from: Dict, start: int, end: int) -> Tuple:
        """Ανακατασκευή διαδρομής από A* αποτελέσματα"""
        path = []
        current = end
        
        while current is not None:
            path.append(current)
            current = came_from.get(current)
        
        path.reverse()
        
        if not path or path[0] != start:
            return None
        
        # Μετατροπή σε coordinates και υπολογισμός στατιστικών
        coords = []
        total_distance = 0
        total_time = 0
        instructions = []
        
        for i, node in enumerate(path):
            if node in self.nodes:
                lat, lon = self.nodes[node]
                coords.append([lon, lat])
                
                if i > 0:
                    prev_node = path[i-1]
                    # Βρες την ακμή για να πάρεις το κόστος
                    for edge_data in self.graph.get(prev_node, []):
                        if len(edge_data) >= 3 and edge_data[0] == node:
                            distance, time_cost = edge_data[1], edge_data[2]
                            total_distance += distance
                            total_time += time_cost
                            
                            # Δημιουργία οδηγίας
                            instructions.append({
                                'distance': distance,
                                'time': time_cost,
                                'instruction': f"Continue for {distance:.2f}km"
                            })
                            break
        
        return coords, total_distance, total_time, instructions
    
    def _update_astar_stats(self, search_time: float, nodes_explored: int):
        """Ενημέρωση στατιστικών A*"""
        self.performance_stats['total_searches'] += 1
        self.performance_stats['astar_searches'] += 1
        self.performance_stats['nodes_explored_astar'] += nodes_explored
        
        # Υπολογισμός μέσου όρου
        current_avg = self.performance_stats['avg_astar_time']
        total_astar = self.performance_stats['astar_searches']
        
        new_avg = ((current_avg * (total_astar - 1)) + search_time) / total_astar
        self.performance_stats['avg_astar_time'] = new_avg
    
    def get_algorithm_stats(self) -> Dict:
        """Επιστροφή στατιστικών απόδοσης αλγορίθμων"""
        stats = self.performance_stats.copy()
        
        if stats['astar_searches'] > 0:
            stats['avg_nodes_per_astar'] = stats['nodes_explored_astar'] / stats['astar_searches']
        else:
            stats['avg_nodes_per_astar'] = 0
            
        if stats['dijkstra_searches'] > 0:
            stats['avg_nodes_per_dijkstra'] = stats['nodes_explored_dijkstra'] / stats['dijkstra_searches']
        else:
            stats['avg_nodes_per_dijkstra'] = 0
        
        # Υπολογισμός speedup
        if stats['avg_dijkstra_time'] > 0 and stats['avg_astar_time'] > 0:
            stats['astar_speedup'] = stats['avg_dijkstra_time'] / stats['avg_astar_time']
        else:
            stats['astar_speedup'] = 0
            
        return stats
    
    def choose_best_algorithm(self, start: int, end: int) -> str:
        """Επιλογή καλύτερου αλγορίθμου βάσει χαρακτηριστικών"""
        if start not in self.nodes or end not in self.nodes:
            return 'dijkstra'
        
        # Υπολογισμός απόστασης
        distance = self.euclidean_heuristic(start, end)
        network_size = len(self.nodes)
        
        # Κριτήρια επιλογής
        if distance > 50:  # Πολύ μεγάλη απόσταση
            return 'astar_adaptive'
        elif distance > 20:  # Μεγάλη απόσταση
            return 'astar_euclidean'
        elif network_size > 10000:  # Μεγάλο δίκτυο
            return 'astar_manhattan'
        else:
            return 'dijkstra'  # Για μικρές αποστάσεις ο Dijkstra είναι αρκετός
