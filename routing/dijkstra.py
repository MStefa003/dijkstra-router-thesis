import heapq
import math
import time
from collections import defaultdict
try:
    from .astar_dijkstra import AStarDijkstra
except ImportError:
    from routing.astar_dijkstra import AStarDijkstra
from functools import lru_cache

class Dijkstra:
    def __init__(self):
        # αρχικοποίηση των δομών δεδομένων
        self.nodes = {}  # node_id -> (lat, lon)
        self.graph = defaultdict(list)  # adjacency list
        self.route_cache = {}  # cache για ταχύτερες επαναλήψεις
        
        # A* integration
        self.astar = AStarDijkstra()
        
        # Performance tracking
        self.performance_stats = {
            'total_searches': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_search_time': 0,
            'algorithm_used': 'dijkstra'  # Τελευταίος αλγόριθμος
        }
    
    def find_nearest_node(self, lat, lon, max_radius=0.5):
        """
        Βρίσκει τον πλησιέστερο κόμβο στις συντεταγμένες που δίνουμε μέσα σε μια συγκεκριμένη ακτίνα
        
        Args:
            lat, lon: Συντεταγμένες σημείου
            max_radius: Μέγιστη απόσταση αναζήτησης σε χλμ
        
        Returns:
            Το ID του κοντινότερου κόμβου ή None αν δεν βρέθηκε κόμβος μέσα στη μέγιστη απόσταση
        """
        close_node = None
        min_dist = float('inf')
        
        # Ψάχνουμε όλους τους κόμβους για τον κοντινότερο
        for node_id, (node_lat, node_lon) in self.nodes.items():
            dist = self.haversine(lon, lat, node_lon, node_lat)
            if dist < min_dist:
                min_dist = dist
                close_node = node_id
        
        # Ελέγχουμε αν βρέθηκε κόμβος μέσα στην επιθυμητή ακτίνα
        if close_node is None or min_dist > max_radius:
            print(f"Δεν βρέθηκε κόμβος μέσα σε ακτίνα {max_radius} χλμ (Κοντινότερος: {min_dist:.2f} χλμ)")
            return None
        
        print(f"Βρέθηκε κόμβος {close_node} σε απόσταση {min_dist:.2f} χλμ")
        return close_node
    
    def _generate_cache_key(self, start_lat, start_lon, end_lat, end_lon):
        """Δημιουργία κλειδιού cache για τη διαδρομή"""
        # Στρογγυλοποίηση συντεταγμένων για καλύτερο caching
        start_key = f"{round(start_lat, 4)},{round(start_lon, 4)}"
        end_key = f"{round(end_lat, 4)},{round(end_lon, 4)}"
        return f"{start_key}->{end_key}"
    
    def get_performance_stats(self):
        """Επιστροφή στατιστικών απόδοσης"""
        if self.performance_stats['total_searches'] > 0:
            hit_rate = (self.performance_stats['cache_hits'] / self.performance_stats['total_searches']) * 100
        else:
            hit_rate = 0
        
        # Συνδυασμός με A* stats
        astar_stats = self.astar.get_algorithm_stats()
            
        return {
            'total_searches': self.performance_stats['total_searches'],
            'cache_hit_rate': f"{hit_rate:.1f}%",
            'avg_search_time': f"{self.performance_stats['avg_search_time']:.3f}s",
            'cache_size': len(self.route_cache),
            'last_algorithm': self.performance_stats['algorithm_used'],
            'astar_searches': astar_stats.get('astar_searches', 0),
            'dijkstra_searches': astar_stats.get('dijkstra_searches', 0),
            'astar_speedup': f"{astar_stats.get('astar_speedup', 0):.1f}x"
        }
    
    def shortest_path(self, start_lat, start_lon, end_lat, end_lon, force_connection=False):
        """Εύρεση συντομότερης διαδρομής με βελτιωμένο Dijkstra"""
        search_start_time = time.time()
        self.performance_stats['total_searches'] += 1
        
        # Έλεγχος cache πρώτα
        cache_key = self._generate_cache_key(start_lat, start_lon, end_lat, end_lon)
        if cache_key in self.route_cache:
            self.performance_stats['cache_hits'] += 1
            print(f"Βρέθηκε διαδρομή στο cache: {cache_key}")
            cached_result = self.route_cache[cache_key]
            return cached_result['geometry'], cached_result['distance'], cached_result['duration'], cached_result['steps']

        self.performance_stats['cache_misses'] += 1
        print(f"Υπολογισμός νέας διαδρομής: {cache_key}")
        
        # Εύρεση των κοντινότερων κόμβων στο οδικό δίκτυο με αυξανόμενη ακτίνα αναζήτησης
        start = None
        end = None
        
        print(f"\nΑναζήτηση κόμβων για τα σημεία ({start_lat:.6f}, {start_lon:.6f}) και ({end_lat:.6f}, {end_lon:.6f})")
        
        # Υπολογισμός απόστασης για επιλογή ακτίνων
        initial_distance = self.haversine(start_lon, start_lat, end_lon, end_lat)
        
        # Βελτιωμένες ακτίνες αναζήτησης βάσει απόστασης
        if initial_distance > 40:  # Για Αίγιο-Πάτρα τύπου
            search_radii = [0.1, 0.3, 0.5, 1.0, 2.0, 5.0]  # Μεγαλύτερες ακτίνες
            print(f"Πολύ μεγάλη απόσταση ({initial_distance:.1f}km) - Χρήση εκτεταμένων ακτίνων")
        elif initial_distance > 20:
            search_radii = [0.05, 0.2, 0.5, 1.0, 2.0]  # Μεσαίες ακτίνες
            print(f"Μεγάλη απόσταση ({initial_distance:.1f}km) - Χρήση μεσαίων ακτίνων")
        else:
            search_radii = [0.05, 0.1, 0.2, 0.5, 1.0]  # Κανονικές ακτίνες
            print(f"Μικρή απόσταση ({initial_distance:.1f}km) - Χρήση κανονικών ακτίνων")
        
        for radius in search_radii:
            start = self.find_nearest_node(start_lat, start_lon, radius)
            if start is not None:
                print(f"  Βρέθηκε κόμβος αφετηρίας με ακτίνα {radius} χλμ")
                break
                
        for radius in search_radii:
            end = self.find_nearest_node(end_lat, end_lon, radius)
            if end is not None:
                print(f"  Βρέθηκε κόμβος προορισμού με ακτίνα {radius} χλμ")
                break
        
        # Αν δεν βρέθηκαν κόμβοι και το force_connection είναι αληθές, προσπαθούμε να βρούμε τους πιο κεντρικούς κόμβους
        if (start is None or end is None) and force_connection and len(self.nodes) > 0:
            print("  Χρήση εξαναγκασμένης σύνδεσης με τους πιο κεντρικούς κόμβους")
            
            # Ευρετική προσέγγιση: χρησιμοποιούμε τους κόμβους με τις περισσότερες συνδέσεις, 
            # οι οποίοι συνήθως είναι κεντρικοί κόμβοι στο οδικό δίκτυο
            
            # Εύρεση των κόμβων με τις περισσότερες συνδέσεις
            connected_nodes = {}
            for node_id in self.graph:
                connected_nodes[node_id] = len(self.graph[node_id])
            
            # Ταξινόμηση κόμβων βάσει των συνδέσεων
            sorted_nodes = sorted(connected_nodes.items(), key=lambda x: x[1], reverse=True)
            
            # Χρήση των πρώτων 10 πιο συνδεδεμένων κόμβων
            top_nodes = [node_id for node_id, _ in sorted_nodes[:10] if node_id in self.nodes]
            
            if start is None and top_nodes:
                # Εύρεση του κοντινότερου στο start από τους top nodes
                start_distances = {}
                for node_id in top_nodes:
                    node_lat, node_lon = self.nodes[node_id]
                    dist = self.haversine(node_lon, node_lat, start_lon, start_lat)
                    start_distances[node_id] = dist
                
                start = min(start_distances, key=start_distances.get)
                print(f"  Επιλέχθηκε κεντρικός κόμβος για αφετηρία: {start} σε απόσταση {start_distances[start]:.2f} χλμ")
            
            if end is None and top_nodes:
                # Εύρεση του κοντινότερου στο end από τους top nodes
                end_distances = {}
                for node_id in top_nodes:
                    node_lat, node_lon = self.nodes[node_id]
                    dist = self.haversine(node_lon, node_lat, end_lon, end_lat)
                    end_distances[node_id] = dist
                
                end = min(end_distances, key=end_distances.get)
                print(f"  Επιλέχθηκε κεντρικός κόμβος για προορισμό: {end} σε απόσταση {end_distances[end]:.2f} χλμ")
        
        if start is None or end is None:
            print(f"Δεν βρέθηκαν κόμβοι κοντά στα σημεία αρχής ή τέλους, ακόμα και με αυξημένη ακτίνα")
            return None, None, None, None
            
        print(f"Υπολογισμός διαδρομής από {start} προς {end}")
        
        # Υπολογισμός απόστασης σε ευθεία γραμμή
        route_direct_distance = self.haversine(
            self.nodes[start][1], self.nodes[start][0],
            self.nodes[end][1], self.nodes[end][0]
        )
        
        print(f"Απόσταση σε ευθεία γραμμή: {route_direct_distance:.2f} χλμ")
        
        # Συγχρονισμός A* δεδομένων
        self.astar.nodes = self.nodes
        self.astar.graph = self.graph
        
        # Επιλογή αλγορίθμου βάσει απόστασης και μεγέθους δικτύου
        algorithm = self.astar.choose_best_algorithm(start, end)
        self.performance_stats['algorithm_used'] = algorithm
        
        if algorithm.startswith('astar'):
            heuristic_type = algorithm.split('_')[1] if '_' in algorithm else 'adaptive'
            print(f"🤖 Χρήση A* με {heuristic_type} heuristic ({route_direct_distance:.1f}km)")
            result = self.astar.a_star_search(start, end, heuristic_type)
        elif route_direct_distance > 25:
            print(f"🔄 Πολύ μεγάλη απόσταση ({route_direct_distance:.1f}km) - Bidirectional Dijkstra")
            result = self._bidirectional_dijkstra(start, end, route_direct_distance)
        elif route_direct_distance > 10:
            print(f"🔄 Μεγάλη απόσταση ({route_direct_distance:.1f}km) - Bidirectional Dijkstra")
            result = self._bidirectional_dijkstra(start, end, route_direct_distance)
        else:
            print(f"🔍 Μικρή απόσταση ({route_direct_distance:.1f}km) - Standard Dijkstra")
            result = self._standard_dijkstra(start, end, route_direct_distance)
        
        if result is None:
            return None, None, None, None
            
        coords, total_dist, total_time, instr = result
        
        # Αποθήκευση στο cache
        search_time = time.time() - search_start_time
        self._update_performance_stats(search_time)
        
        cache_result = {
            'geometry': coords,
            'distance': total_dist,
            'duration': total_time,
            'steps': instr
        }
        self.route_cache[cache_key] = cache_result
        
        print(f"Διαδρομή υπολογίστηκε σε {search_time:.3f} δευτερόλεπτα")
        return coords, total_dist, total_time, instr
    
    def _update_performance_stats(self, search_time):
        """Ενημέρωση στατιστικών απόδοσης"""
        current_avg = self.performance_stats['avg_search_time']
        total_searches = self.performance_stats['total_searches']
        
        # Υπολογισμός νέου μέσου όρου
        new_avg = ((current_avg * (total_searches - 1)) + search_time) / total_searches
        self.performance_stats['avg_search_time'] = new_avg
    
    def _standard_dijkstra(self, start, end, route_direct_distance):
        """Κλασικός αλγόριθμος Dijkstra για μικρές αποστάσεις"""
            
        # αρχικοποίηση μεταβλητών Dijkstra
        distances = {node: float('infinity') for node in self.graph}
        distances[start] = 0
        times = {node: float('infinity') for node in self.nodes}
        times[start] = 0
        prev_nodes = {node: None for node in self.nodes}
        
        # ουρά προτεραιότητας ([χρόνος, απόσταση, κόμβος])
        pq = [(0, 0, start)]
        
        # Προσαρμοστικά όρια βάσει απόστασης και μεγέθους δικτύου
        if route_direct_distance > 40:  # Για πολύ μεγάλες αποστάσεις
            MAX_VISITED = min(500000, len(self.nodes))  # Περισσότερες επισκέψεις
            MAX_DISTANCE = route_direct_distance * 5  # Μεγαλύτερο όριο απόστασης
            print(f"Όρια για πολύ μεγάλη απόσταση: {MAX_VISITED} επισκέψεις, {MAX_DISTANCE:.1f}km max")
        elif route_direct_distance > 20:
            MAX_VISITED = min(200000, len(self.nodes))
            MAX_DISTANCE = route_direct_distance * 4
        else:
            MAX_VISITED = min(100000, len(self.nodes))
            MAX_DISTANCE = route_direct_distance * 3
        
        # ουρά προτεραιότητας για κόμβους που θα επισκεφτούμε
        # ο αλγόριθμος συνεχίζει έως ότου επισκεφτούμε όλους τους κόμβους
        # ή μέχρι να φτάσουμε στον προορισμό μας
        visited = set()
        
        while pq:
            # παίρνουμε τον κόμβο με την ελάχιστη απόσταση/χρόνο
            curr_time, curr_dist, curr_node = heapq.heappop(pq)
            
            # αν έχουμε ήδη επισκεφτεί αυτόν τον κόμβο, τον αγνοούμε
            if curr_node in visited:
                continue
                
            # επισκεπτόμαστε αυτόν τον κόμβο
            visited.add(curr_node)
            
            # αν φτάσαμε στο όριο επισκέψεων, σταματάμε την αναζήτηση
            if len(visited) > MAX_VISITED:
                print(f"Προειδοποίηση: Έχουμε επισκεφτεί ήδη {MAX_VISITED} κόμβους. Τερματισμός αναζήτησης.")
                break
                
            # αν αυτός ο κόμβος είναι ο προορισμός μας, σταματάμε
            if curr_node == end:
                print(f"Βρήκαμε τον προορισμό μετά από {len(visited)} επισκέψεις")
                break
                
            # αν η απόσταση είναι ήδη πολύ μεγάλη, παραλείπουμε αυτόν τον κόμβο
            if curr_dist > MAX_DISTANCE:
                continue
                
            # ελέγχουμε όλους τους γείτονες αυτού του κόμβου
            for edge_data in self.graph.get(curr_node, []):
                # Χειρισμός διαφορετικών μορφών edge data
                if len(edge_data) == 3:
                    # Παλιά μορφή: (neighbor, dist, time)
                    neighbor, dist, time = edge_data
                elif len(edge_data) == 4:
                    # Νέα μορφή: (neighbor, dist, time, road_info)
                    neighbor, dist, time, road_info = edge_data
                else:
                    continue  # Αγνοούμε μη αναμενόμενες μορφές
                
                # υπολογίζουμε τη νέα απόσταση/χρόνο
                new_dist = curr_dist + dist
                new_time = curr_time + time
                
                # αν βρήκαμε συντομότερη διαδρομή, την ενημερώνουμε
                if new_dist < distances.get(neighbor, float('infinity')):
                    distances[neighbor] = new_dist
                    times[neighbor] = new_time
                    prev_nodes[neighbor] = curr_node
                    
                    # προσθέτουμε αυτόν τον κόμβο στην ουρά για επίσκεψη
                    heapq.heappush(pq, (new_time, new_dist, neighbor))
        
        # αν δεν υπάρχει διαδρομή, επιστρέφει None
        if prev_nodes[end] is None:
            print("Δε βρέθηκε διαδρομή")
            return None
            
        return self._reconstruct_path(prev_nodes, start, end)
    
    def _bidirectional_dijkstra(self, start, end, route_direct_distance):
        """Bidirectional Dijkstra για μεγάλες αποστάσεις - 2x ταχύτερος"""
        # Αρχικοποίηση για forward search
        forward_distances = {node: float('infinity') for node in self.graph}
        forward_distances[start] = 0
        forward_prev = {node: None for node in self.nodes}
        forward_pq = [(0, 0, start)]
        forward_visited = set()
        
        # Αρχικοποίηση για backward search
        backward_distances = {node: float('infinity') for node in self.graph}
        backward_distances[end] = 0
        backward_prev = {node: None for node in self.nodes}
        backward_pq = [(0, 0, end)]
        backward_visited = set()
        
        # Κοινές μεταβλητές με προσαρμοστικά όρια
        best_distance = float('infinity')
        meeting_node = None
        
        # Προσαρμοστικά όρια για bidirectional search
        if route_direct_distance > 40:  # Πολύ μεγάλες αποστάσεις
            MAX_VISITED = min(200000, len(self.nodes) // 2)
            print(f"Bidirectional search με εκτεταμένα όρια: {MAX_VISITED} επισκέψεις ανά κατεύθυνση")
        elif route_direct_distance > 20:
            MAX_VISITED = min(100000, len(self.nodes) // 2)
        else:
            MAX_VISITED = min(50000, len(self.nodes) // 2)
        
        visited_count = 0
        
        while forward_pq and backward_pq and visited_count < MAX_VISITED:
            # Εναλλαγή μεταξύ forward και backward search
            if len(forward_pq) <= len(backward_pq):
                # Forward step
                if forward_pq:
                    curr_time, curr_dist, curr_node = heapq.heappop(forward_pq)
                    
                    if curr_node in forward_visited:
                        continue
                        
                    forward_visited.add(curr_node)
                    visited_count += 1
                    
                    # Έλεγχος αν συναντήσαμε το backward search
                    if curr_node in backward_visited:
                        total_dist = forward_distances[curr_node] + backward_distances[curr_node]
                        if total_dist < best_distance:
                            best_distance = total_dist
                            meeting_node = curr_node
                            print(f"Συνάντηση στον κόμβο {meeting_node} με απόσταση {best_distance:.2f} χλμ")
                            break
                    
                    # Επέκταση forward search
                    for edge_data in self.graph.get(curr_node, []):
                        # Χειρισμός διαφορετικών μορφών edge data
                        if len(edge_data) >= 3:
                            neighbor, dist, time = edge_data[:3]
                        else:
                            continue
                            
                        new_dist = curr_dist + dist
                        new_time = curr_time + time
                        
                        if new_dist < forward_distances.get(neighbor, float('infinity')):
                            forward_distances[neighbor] = new_dist
                            forward_prev[neighbor] = curr_node
                            heapq.heappush(forward_pq, (new_time, new_dist, neighbor))
            else:
                # Backward step
                if backward_pq:
                    curr_time, curr_dist, curr_node = heapq.heappop(backward_pq)
                    
                    if curr_node in backward_visited:
                        continue
                        
                    backward_visited.add(curr_node)
                    visited_count += 1
                    
                    # Έλεγχος αν συναντήσαμε το forward search
                    if curr_node in forward_visited:
                        total_dist = forward_distances[curr_node] + backward_distances[curr_node]
                        if total_dist < best_distance:
                            best_distance = total_dist
                            meeting_node = curr_node
                            print(f"Συνάντηση στον κόμβο {meeting_node} με απόσταση {best_distance:.2f} χλμ")
                            break
                    
                    # Επέκταση backward search
                    for edge_data in self.graph.get(curr_node, []):
                        # Χειρισμός διαφορετικών μορφών edge data
                        if len(edge_data) >= 3:
                            neighbor, dist, time = edge_data[:3]
                        else:
                            continue
                            
                        new_dist = curr_dist + dist
                        new_time = curr_time + time
                        
                        if new_dist < backward_distances.get(neighbor, float('infinity')):
                            backward_distances[neighbor] = new_dist
                            backward_prev[neighbor] = curr_node
                            heapq.heappush(backward_pq, (new_time, new_dist, neighbor))
        
        if meeting_node is None:
            print("Δε βρέθηκε διαδρομή με bidirectional search")
            return None
        
        efficiency_gain = ((MAX_VISITED * 2) - visited_count) / (MAX_VISITED * 2) * 100
        print(f"Bidirectional search ολοκληρώθηκε με {visited_count} επισκέψεις")
        print(f"Εξοικονόμηση: {efficiency_gain:.1f}% λιγότερες επισκέψεις από κλασικό Dijkstra")
        
        # Ανακατασκευή διαδρομής από start -> meeting_node -> end
        return self._reconstruct_bidirectional_path(forward_prev, backward_prev, start, end, meeting_node)
    
    def _reconstruct_path(self, prev_nodes, start, end):
        """Ανακατασκευή διαδρομής από τον πίνακα προηγούμενων κόμβων"""
        path = []
        current = end
        # ξεκινάμε από το τέλος και πάμε προς την αρχή
        while current:
            path.append(current)
            current = prev_nodes[current]
        # αναστρέφουμε τη λίστα για να πάρουμε τη σωστή σειρά
        path.reverse()
        
        return self._path_to_coordinates(path)
    
    def _reconstruct_bidirectional_path(self, forward_prev, backward_prev, start, end, meeting_node):
        """Ανακατασκευή διαδρομής από bidirectional search"""
        # Forward path: start -> meeting_node
        forward_path = []
        current = meeting_node
        while current is not None:
            forward_path.append(current)
            current = forward_prev[current]
        forward_path.reverse()
        
        # Backward path: meeting_node -> end
        backward_path = []
        current = meeting_node
        while current is not None:
            backward_path.append(current)
            current = backward_prev[current]
        
        # Συνδυασμός paths (αφαιρούμε το διπλό meeting_node)
        full_path = forward_path + backward_path[1:]
        
        return self._path_to_coordinates(full_path)
    
    def _path_to_coordinates(self, path):
        """Μετατροπή path κόμβων σε συντεταγμένες και υπολογισμός μετρικών"""
        
        coords = []
        instr = []  # οδηγίες για κάθε βήμα
        
        previous_lon = None
        previous_lat = None
        total_dist = 0
        total_time = 0
        
        for i, node in enumerate(path):
            lat, lon = self.nodes[node]
            coords.append([lon, lat])
            
            # Υπολογισμός πληροφοριών για το βήμα
            if previous_lon is not None and previous_lat is not None:
                step_dist = self.haversine(previous_lon, previous_lat, lon, lat)
                total_dist += step_dist
                
                # Βελτιωμένος υπολογισμός χρόνου με εκτίμηση ταχύτητας
                estimated_speed = self._estimate_speed_between_nodes(path[i-1], node)
                step_time = (step_dist / estimated_speed) * 3600  # δευτερόλεπτα
                total_time += step_time
                
                # Υπολογισμός κατεύθυνσης κίνησης
                direction = self.get_direction(previous_lat, previous_lon, lat, lon)
                
                instr.append({
                    'instruction': direction,
                    'distance': step_dist,
                    'duration': step_time
                })
                
            previous_lat = lat
            previous_lon = lon
        
        return coords, total_dist, total_time, instr
    
    def _estimate_speed_between_nodes(self, node1, node2):
        """Εκτίμηση ταχύτητας μεταξύ δύο κόμβων βάσει του τύπου δρόμου"""
        # Προεπιλεγμένη ταχύτητα αν δεν βρούμε πληροφορίες
        default_speed = 50  # km/h
        
        # Εύρεση της ακμής μεταξύ των κόμβων στο γράφημα
        for edge_data in self.graph.get(node1, []):
            if len(edge_data) == 3:
                # Παλιά μορφή: (neighbor, dist, time)
                neighbor, dist, time = edge_data
            elif len(edge_data) == 4:
                # Νέα μορφή: (neighbor, dist, time, road_info)
                neighbor, dist, time, road_info = edge_data
            else:
                continue  # Αγνοούμε μη αναμενόμενες μορφές
            
            # Υπολογισμός ταχύτητας από απόσταση και χρόνο
            if neighbor == node2 and time > 0:
                speed = (dist / (time / 3600))  # km/h
                return max(20, min(120, speed))  # Όρια 20-120 km/h
        
        return default_speed
    
    def compare_algorithms(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float):
        """Σύγκριση αλγορίθμων A* vs Dijkstra"""
        # Εύρεση κόμβων
        start = self.find_nearest_node(start_lat, start_lon)
        end = self.find_nearest_node(end_lat, end_lon)
        
        if not start or not end:
            return {'error': 'Δεν βρέθηκαν κόμβοι'}
        
        # Συγχρονισμός A* δεδομένων
        self.astar.nodes = self.nodes
        self.astar.graph = self.graph
        
        return self.astar.compare_algorithms(start, end)
        
    def haversine(self, lon1, lat1, lon2, lat2):
        """
        Υπολογισμός απόστασης μεταξύ δύο σημείων στη Γη
        χρησιμοποιοώντας τον τύπο haversine
        """
        # Μετατροπή από μοίρες σε ακτίνια
        lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
        
        # Τύπος haversine
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Ακτίνα της Γης σε χιλιόμετρα
        return c * r
    
    # προσθήκη συνάρτησης για υπολογισμό κατεύθυνσης κίνησης
    def get_direction(self, lat1, lon1, lat2, lon2):
        # Υπολογισμός της γωνίας μεταξύ δύο σημείων
        angle = math.atan2(lon2 - lon1, lat2 - lat1) * 180 / math.pi
        
        # Ανάλογα με τη γωνία, επιστρέφουμε την κατεύθυνση
        if -22.5 <= angle < 22.5:
            return "Συνέχεια βόρεια"
        elif 22.5 <= angle < 67.5:
            return "Στροφή βορειοανατολικά"
        elif 67.5 <= angle < 112.5:
            return "Στροφή ανατολικά"
        elif 112.5 <= angle < 157.5:
            return "Στροφή νοτιοανατολικά"
        elif 157.5 <= angle <= 180 or -180 <= angle < -157.5:
            return "Στροφή νότια"
        elif -157.5 <= angle < -112.5:
            return "Στροφή νοτιοδυτικά"
        elif -112.5 <= angle < -67.5:
            return "Στροφή δυτικά"
        elif -67.5 <= angle < -22.5:
            return "Στροφή βορειοδυτικά"
        
        return "Συνέχεια ευθεία" # αυτό δεν θα συμβεί ποτέ, αλλά για καλό και για κακό
    
    def clear_cache(self):
        """Καθαρισμός cache"""
        self.route_cache.clear()
        print("🗑️ Route cache καθαρίστηκε")
    
    def get_algorithm_comparison(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float):
        """Λήψη σύγκρισης αλγορίθμων"""
        return self.compare_algorithms(start_lat, start_lon, end_lat, end_lon)
    
    def get_cache_size(self):
        """Επιστρέφει το μέγεθος του cache"""
        return len(self.route_cache)
