import heapq
import logging
import math
import time
import collections
from collections import defaultdict
try:
    from .astar_dijkstra import AStarDijkstra
except ImportError:
    from routing.astar_dijkstra import AStarDijkstra
from functools import lru_cache

logger = logging.getLogger(__name__)

class Dijkstra:
    def __init__(self):
        # αρχικοποίηση των δομών δεδομένων
        self.nodes = {}  # node_id -> (lat, lon)
        self.graph = defaultdict(list)  # adjacency list
        self.route_cache = collections.OrderedDict()  # LRU cache

        # Spatial index for fast nearest-node lookup
        self._kdtree = None
        self._kdtree_ids = None
        self._kdtree_coords = None
        self._cos_lat = 1.0  # longitude scaling factor for KD-tree equirectangular correction

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

    def _build_spatial_index(self):
        """Κατασκευή KD-tree για γρήγορη αναζήτηση κοντινότερου κόμβου (O(log n) αντί O(n))"""
        try:
            import numpy as np
            from scipy.spatial import cKDTree

            if not self.nodes:
                self._kdtree = None
                return

            self._kdtree_ids = list(self.nodes.keys())
            self._kdtree_coords = [self.nodes[n] for n in self._kdtree_ids]  # (lat, lon)
            # Equirectangular correction: scale lon by cos(mean_lat) so that Euclidean
            # distance in the tree approximates true surface distance.
            lats = [c[0] for c in self._kdtree_coords]
            self._cos_lat = math.cos(math.radians(sum(lats) / len(lats)))
            scaled = [(lat, lon * self._cos_lat) for lat, lon in self._kdtree_coords]
            self._kdtree = cKDTree(np.array(scaled))
            logger.debug("KD-tree κατασκευάστηκε με %d κόμβους", len(self._kdtree_ids))
        except ImportError:
            self._kdtree = None
            logger.warning("scipy μη διαθέσιμο — χρήση γραμμικής αναζήτησης κόμβων")
        except Exception as e:
            self._kdtree = None
            logger.warning("Σφάλμα κατασκευής KD-tree: %s", e)

    def find_nearest_node(self, lat, lon, max_radius=0.5):
        """
        Βρίσκει τον πλησιέστερο κόμβο στις συντεταγμένες που δίνουμε μέσα σε μια συγκεκριμένη ακτίνα.
        Χρησιμοποιεί KD-tree αν είναι διαθέσιμο (O(log n)), αλλιώς γραμμική αναζήτηση (O(n)).

        Args:
            lat, lon: Συντεταγμένες σημείου
            max_radius: Μέγιστη απόσταση αναζήτησης σε χλμ

        Returns:
            Το ID του κοντινότερου κόμβου ή None αν δεν βρέθηκε κόμβος μέσα στη μέγιστη απόσταση
        """
        # --- Fast path: KD-tree lookup ---
        if self._kdtree is not None and self._kdtree_ids:
            _, idx = self._kdtree.query([lat, lon * self._cos_lat], k=1)
            if idx < len(self._kdtree_ids):
                node_id = self._kdtree_ids[idx]
                node_lat, node_lon = self._kdtree_coords[idx]
                dist = self.haversine(lon, lat, node_lon, node_lat)
                if dist <= max_radius:
                    logger.debug("Βρέθηκε κόμβος %s σε απόσταση %.3f χλμ (KD-tree)", node_id, dist)
                    return node_id
                else:
                    logger.debug("Κοντινότερος κόμβος %.3f χλμ > ακτίνα %s χλμ", dist, max_radius)
            return None

        # --- Fallback: linear scan ---
        close_node = None
        min_dist = float('inf')

        for node_id, (node_lat, node_lon) in self.nodes.items():
            dist = self.haversine(lon, lat, node_lon, node_lat)
            if dist < min_dist:
                min_dist = dist
                close_node = node_id

        if close_node is None or min_dist > max_radius:
            logger.debug("Δεν βρέθηκε κόμβος μέσα σε ακτίνα %s χλμ (Κοντινότερος: %.2f χλμ)", max_radius, min_dist)
            return None

        logger.debug("Βρέθηκε κόμβος %s σε απόσταση %.2f χλμ", close_node, min_dist)
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
            self.route_cache.move_to_end(cache_key)
            logger.debug("Βρέθηκε διαδρομή στο cache: %s", cache_key)
            cached_result = self.route_cache[cache_key]
            return cached_result['geometry'], cached_result['distance'], cached_result['duration'], cached_result['steps']

        self.performance_stats['cache_misses'] += 1
        logger.debug("Υπολογισμός νέας διαδρομής: %s", cache_key)

        # Εύρεση των κοντινότερων κόμβων στο οδικό δίκτυο με αυξανόμενη ακτίνα αναζήτησης
        start = None
        end = None

        logger.debug("Αναζήτηση κόμβων για τα σημεία (%.6f, %.6f) και (%.6f, %.6f)",
                     start_lat, start_lon, end_lat, end_lon)

        # Υπολογισμός απόστασης για επιλογή ακτίνων
        initial_distance = self.haversine(start_lon, start_lat, end_lon, end_lat)

        # Βελτιωμένες ακτίνες αναζήτησης βάσει απόστασης
        if initial_distance > 40:  # Για Αίγιο-Πάτρα τύπου
            search_radii = [0.1, 0.3, 0.5, 1.0, 2.0, 5.0]  # Μεγαλύτερες ακτίνες
            logger.debug("Πολύ μεγάλη απόσταση (%.1fkm) - Χρήση εκτεταμένων ακτίνων", initial_distance)
        elif initial_distance > 20:
            search_radii = [0.05, 0.2, 0.5, 1.0, 2.0]  # Μεσαίες ακτίνες
            logger.debug("Μεγάλη απόσταση (%.1fkm) - Χρήση μεσαίων ακτίνων", initial_distance)
        else:
            search_radii = [0.05, 0.1, 0.2, 0.5, 1.0]  # Κανονικές ακτίνες
            logger.debug("Μικρή απόσταση (%.1fkm) - Χρήση κανονικών ακτίνων", initial_distance)

        for radius in search_radii:
            start = self.find_nearest_node(start_lat, start_lon, radius)
            if start is not None:
                logger.debug("  Βρέθηκε κόμβος αφετηρίας με ακτίνα %s χλμ", radius)
                break

        for radius in search_radii:
            end = self.find_nearest_node(end_lat, end_lon, radius)
            if end is not None:
                logger.debug("  Βρέθηκε κόμβος προορισμού με ακτίνα %s χλμ", radius)
                break

        # Αν δεν βρέθηκαν κόμβοι και το force_connection είναι αληθές, προσπαθούμε να βρούμε τους πιο κεντρικούς κόμβους
        if (start is None or end is None) and force_connection and len(self.nodes) > 0:
            logger.debug("  Χρήση εξαναγκασμένης σύνδεσης με τους πιο κεντρικούς κόμβους")

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
                logger.debug("  Επιλέχθηκε κεντρικός κόμβος για αφετηρία: %s σε απόσταση %.2f χλμ",
                             start, start_distances[start])

            if end is None and top_nodes:
                # Εύρεση του κοντινότερου στο end από τους top nodes
                end_distances = {}
                for node_id in top_nodes:
                    node_lat, node_lon = self.nodes[node_id]
                    dist = self.haversine(node_lon, node_lat, end_lon, end_lat)
                    end_distances[node_id] = dist

                end = min(end_distances, key=end_distances.get)
                logger.debug("  Επιλέχθηκε κεντρικός κόμβος για προορισμό: %s σε απόσταση %.2f χλμ",
                             end, end_distances[end])

        if start is None or end is None:
            logger.warning("Δεν βρέθηκαν κόμβοι κοντά στα σημεία αρχής ή τέλους, ακόμα και με αυξημένη ακτίνα")
            return None, None, None, None

        logger.debug("Υπολογισμός διαδρομής από %s προς %s", start, end)

        # Υπολογισμός απόστασης σε ευθεία γραμμή
        route_direct_distance = self.haversine(
            self.nodes[start][1], self.nodes[start][0],
            self.nodes[end][1], self.nodes[end][0]
        )

        logger.debug("Απόσταση σε ευθεία γραμμή: %.2f χλμ", route_direct_distance)

        # Συγχρονισμός A* δεδομένων
        self.astar.nodes = self.nodes
        self.astar.graph = self.graph

        # Επιλογή αλγορίθμου βάσει απόστασης και μεγέθους δικτύου
        algorithm = self.astar.choose_best_algorithm(start, end)
        self.performance_stats['algorithm_used'] = algorithm

        if algorithm.startswith('astar'):
            heuristic_type = algorithm.split('_')[1] if '_' in algorithm else 'adaptive'
            logger.debug("Χρήση A* με %s heuristic (%.1fkm)", heuristic_type, route_direct_distance)
            result = self.astar.a_star_search(start, end, heuristic_type)
        elif route_direct_distance > 25:
            logger.debug("Πολύ μεγάλη απόσταση (%.1fkm) - Bidirectional Dijkstra", route_direct_distance)
            result = self._bidirectional_dijkstra(start, end, route_direct_distance)
        elif route_direct_distance > 10:
            logger.debug("Μεγάλη απόσταση (%.1fkm) - Bidirectional Dijkstra", route_direct_distance)
            result = self._bidirectional_dijkstra(start, end, route_direct_distance)
        else:
            logger.debug("Μικρή απόσταση (%.1fkm) - Standard Dijkstra", route_direct_distance)
            result = self._standard_dijkstra(start, end, route_direct_distance)

        if result is None:
            return None, None, None, None

        coords, total_dist, total_time, instr = result

        # Αποθήκευση στο cache (LRU eviction: max 200 entries)
        search_time = time.time() - search_start_time
        self._update_performance_stats(search_time)

        if len(self.route_cache) >= 200:
            self.route_cache.popitem(last=False)  # evict LRU

        cache_result = {
            'geometry': coords,
            'distance': total_dist,
            'duration': total_time,
            'steps': instr
        }
        self.route_cache[cache_key] = cache_result

        logger.debug("Διαδρομή υπολογίστηκε σε %.3f δευτερόλεπτα", search_time)
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

        # αρχικοποίηση μεταβλητών Dijkstra (sparse dicts — γρηγορότερα και λιγότερη μνήμη)
        distances = {start: 0.0}
        times = {start: 0.0}
        prev_nodes = {start: None}

        # ουρά προτεραιότητας ([χρόνος, απόσταση, κόμβος])
        pq = [(0, 0, start)]

        # Προσαρμοστικά όρια βάσει απόστασης και μεγέθους δικτύου
        if route_direct_distance > 40:  # Για πολύ μεγάλες αποστάσεις
            MAX_VISITED = min(500000, len(self.nodes))  # Περισσότερες επισκέψεις
            MAX_DISTANCE = route_direct_distance * 5  # Μεγαλύτερο όριο απόστασης
            logger.debug("Όρια για πολύ μεγάλη απόσταση: %d επισκέψεις, %.1fkm max", MAX_VISITED, MAX_DISTANCE)
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
                logger.warning("Προειδοποίηση: Έχουμε επισκεφτεί ήδη %d κόμβους. Τερματισμός αναζήτησης.", MAX_VISITED)
                break

            # αν αυτός ο κόμβος είναι ο προορισμός μας, σταματάμε
            if curr_node == end:
                logger.debug("Βρήκαμε τον προορισμό μετά από %d επισκέψεις", len(visited))
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

                # Χαλάρωση βάσει ΧΡΟΝΟΥ (όχι απόστασης) — βρίσκουμε τη γρηγορότερη διαδρομή
                if new_time < times.get(neighbor, float('infinity')):
                    times[neighbor] = new_time
                    distances[neighbor] = new_dist
                    prev_nodes[neighbor] = curr_node

                    # προσθέτουμε αυτόν τον κόμβο στην ουρά για επίσκεψη
                    heapq.heappush(pq, (new_time, new_dist, neighbor))

        # αν δεν υπάρχει διαδρομή, επιστρέφει None
        if end not in prev_nodes:
            logger.warning("Δε βρέθηκε διαδρομή")
            return None

        return self._reconstruct_path(prev_nodes, start, end)

    def _bidirectional_dijkstra(self, start, end, route_direct_distance):
        """
        Bidirectional Dijkstra με σωστή συνθήκη τερματισμού.
        Ο αλγόριθμος τερματίζει όταν το άθροισμα των κορυφών των δύο ουρών
        υπερβαίνει το βέλτιστο γνωστό κόστος — εγγυάται βέλτιστο αποτέλεσμα.
        Χρόνος ως κόστος (seconds) παντού για συνέπεια.
        """
        if route_direct_distance > 40:
            MAX_VISITED = min(300000, len(self.nodes))
        elif route_direct_distance > 20:
            MAX_VISITED = min(150000, len(self.nodes))
        else:
            MAX_VISITED = min(80000, len(self.nodes))

        # Forward search (από start)
        forward_cost = {}   # node -> best time from start
        forward_cost[start] = 0.0
        forward_prev = {start: None}
        forward_pq = [(0.0, start)]
        forward_settled = set()

        # Backward search (από end, χρησιμοποιεί το ίδιο γράφημα — αποδεκτή προσέγγιση
        # για κυρίως αμφίδρομα οδικά δίκτυα)
        backward_cost = {}
        backward_cost[end] = 0.0
        backward_prev = {end: None}
        backward_pq = [(0.0, end)]
        backward_settled = set()

        best_cost = float('inf')
        meeting_node = None
        total_visited = 0

        while forward_pq and backward_pq and total_visited < MAX_VISITED:
            # Βέλτιστη συνθήκη τερματισμού: όταν και οι δύο κορυφές ≥ best_cost
            # δεν μπορεί να υπάρξει καλύτερη διαδρομή
            if forward_pq[0][0] + backward_pq[0][0] >= best_cost:
                break

            # Επέκταση της κατεύθυνσης με μικρότερο κόστος κορυφής (ισορροπία αναζήτησης)
            if forward_pq[0][0] <= backward_pq[0][0]:
                _, curr_node = heapq.heappop(forward_pq)
                if curr_node in forward_settled:
                    continue
                forward_settled.add(curr_node)
                total_visited += 1

                for edge_data in self.graph.get(curr_node, []):
                    if len(edge_data) < 3:
                        continue
                    neighbor, _, time_cost = edge_data[0], edge_data[1], edge_data[2]
                    new_cost = forward_cost[curr_node] + time_cost
                    if new_cost < forward_cost.get(neighbor, float('inf')):
                        forward_cost[neighbor] = new_cost
                        forward_prev[neighbor] = curr_node
                        heapq.heappush(forward_pq, (new_cost, neighbor))

                        # Έλεγχος σύζευξης με backward search
                        if neighbor in backward_settled:
                            candidate = new_cost + backward_cost[neighbor]
                            if candidate < best_cost:
                                best_cost = candidate
                                meeting_node = neighbor
            else:
                _, curr_node = heapq.heappop(backward_pq)
                if curr_node in backward_settled:
                    continue
                backward_settled.add(curr_node)
                total_visited += 1

                for edge_data in self.graph.get(curr_node, []):
                    if len(edge_data) < 3:
                        continue
                    neighbor, _, time_cost = edge_data[0], edge_data[1], edge_data[2]
                    new_cost = backward_cost[curr_node] + time_cost
                    if new_cost < backward_cost.get(neighbor, float('inf')):
                        backward_cost[neighbor] = new_cost
                        backward_prev[neighbor] = curr_node
                        heapq.heappush(backward_pq, (new_cost, neighbor))

                        # Έλεγχος σύζευξης με forward search
                        if neighbor in forward_settled:
                            candidate = new_cost + forward_cost[neighbor]
                            if candidate < best_cost:
                                best_cost = candidate
                                meeting_node = neighbor

        if meeting_node is None:
            logger.warning("Bidirectional search: δεν βρέθηκε διαδρομή, εναλλαγή σε Standard Dijkstra")
            return self._standard_dijkstra(start, end, route_direct_distance)

        logger.debug("Bidirectional ολοκληρώθηκε: %d επισκέψεις, meeting@%s, κόστος=%.1fs",
                     total_visited, meeting_node, best_cost)
        return self._reconstruct_bidirectional_path(forward_prev, backward_prev, start, end, meeting_node)

    def _reconstruct_path(self, prev_nodes, start, end):
        """Ανακατασκευή διαδρομής από τον πίνακα προηγούμενων κόμβων"""
        path = []
        current = end
        # ξεκινάμε από το τέλος και πάμε προς την αρχή
        while current is not None:
            path.append(current)
            current = prev_nodes.get(current)
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
            current = forward_prev.get(current)
        forward_path.reverse()

        # Backward path: meeting_node -> end  (backward_prev traces forward edges from end)
        backward_path = []
        current = backward_prev.get(meeting_node)
        while current is not None:
            backward_path.append(current)
            current = backward_prev.get(current)

        # Συνδυασμός paths
        full_path = forward_path + backward_path
        return self._path_to_coordinates(full_path)

    def _path_to_coordinates(self, path):
        """Μετατροπή path κόμβων σε συντεταγμένες και υπολογισμός μετρικών"""

        coords = []
        instr = []  # οδηγίες για κάθε βήμα

        previous_lon = None
        previous_lat = None
        previous_node = None
        total_dist = 0
        total_time = 0

        for node in path:
            if node not in self.nodes:
                continue
            lat, lon = self.nodes[node]
            coords.append([lon, lat])

            # Υπολογισμός πληροφοριών για το βήμα
            if previous_lon is not None and previous_lat is not None:
                step_dist = self.haversine(previous_lon, previous_lat, lon, lat)
                total_dist += step_dist

                # Βελτιωμένος υπολογισμός χρόνου με εκτίμηση ταχύτητας
                estimated_speed = self._estimate_speed_between_nodes(previous_node, node)
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
            previous_node = node

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
        logger.debug("Route cache καθαρίστηκε")

    def get_algorithm_comparison(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float):
        """Λήψη σύγκρισης αλγορίθμων"""
        return self.compare_algorithms(start_lat, start_lon, end_lat, end_lon)

    def get_cache_size(self):
        """Επιστρέφει το μέγεθος του cache"""
        return len(self.route_cache)
