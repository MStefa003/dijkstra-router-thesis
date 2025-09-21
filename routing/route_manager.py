from routing.dijkstra import Dijkstra
from routing.osm_handler import OSMHandler
from routing.osrm_helper import OSRMHelper
from routing.live_traffic_manager import LiveTrafficManager

class RouteManager:
    # διαχείριση διαδρομών και σύνδεση Dijkstra/OSM/OSRM
    
    def __init__(self):
        # αρχικοποίηση των βασικών συστατικών
        self.dijkstra = Dijkstra()
        self.osm_handler = OSMHandler(self.dijkstra)
        self.osrm_helper = OSRMHelper()  # Προσθήκη του OSRM helper
        self.live_traffic_manager = LiveTrafficManager()  # Live traffic integration
        
    def find_route(self, start_coords, end_coords, route_type='driving', waypoints=None):
        # Εύρεση διαδρομής με βελτιωμένο Dijkstra και υποστήριξη waypoints
        # μερικοί έλεγχοι για τα input
        if not start_coords or not end_coords:
            print("Λείπουν συντεταγμένες αρχής ή τέλους!")
            return None, None, None, None
        
        # Εναλλακτική διαχείριση για waypoints
        if waypoints and len(waypoints) > 0:
            return self._find_route_with_waypoints(start_coords, end_coords, waypoints, route_type)
        
        # λήψη και κατασκευή του οδικού δικτύου από το OSM
        # αύξηση του buffer για μεγάλες αποστάσεις
        self.check_and_adjust_buffer(start_coords, end_coords)
        
        if not self.osm_handler.download_road_network(start_coords, end_coords):
            print("αποτυχια στη λήψη οδικού δικτύου!")
            return None, None, None, None
            
        # Διαγνωστικά μηνύματα για αποσφαλμάτωση
        print(f"\n\n=== ΕΥΡΕΣΗ ΔΙΑΔΡΟΜΗΣ ΑΠΟ {start_coords} ΣΕ {end_coords} ===")
        print(f"Μέγεθος οδικού δικτύου: {len(self.dijkstra.nodes)} κόμβοι, {len(self.dijkstra.graph)} συνδεδεμένοι κόμβοι\n")
        
        # εύρεση συντομότερης διαδρομής με βελτιωμένο dijkstra
        print(f"Εκκίνηση αλγορίθμου δρομολόγησης...")
        geometry, distance, duration, steps = self.dijkstra.shortest_path(
            start_coords[1], start_coords[0],  # μετατροπή από [lon, lat] σε [lat, lon]
            end_coords[1], end_coords[0],
            force_connection=True  # Προσπάθεια να εξαναγκαστεί η σύνδεση μεταξύ των σημείων
        )
        
        # έλεγχος αν βρέθηκε διαδρομή και fallback με μεγαλύτερο buffer
        if not geometry:
            print("Δε βρέθηκε διαδρομή - δοκιμή με μεγαλύτερο buffer...")
            
            # Αύξηση buffer και επανάληψη
            original_buffer = self.osm_handler.buffer
            self.osm_handler.buffer = min(1.0, original_buffer * 2)  # Διπλασιασμός, μέχρι 1.0
            
            print(f"Επανάληψη με buffer {self.osm_handler.buffer} μοίρες...")
            
            # Νέα λήψη οδικού δικτύου
            if self.osm_handler.download_road_network(start_coords, end_coords):
                geometry, distance, duration, steps = self.dijkstra.shortest_path(
                    start_coords[1], start_coords[0],
                    end_coords[1], end_coords[0],
                    force_connection=True
                )
            
            # Επαναφορά του αρχικού buffer
            self.osm_handler.buffer = original_buffer
            
            if not geometry:
                print("Δε βρέθηκε διαδρομή ούτε με μεγαλύτερο buffer!")
                return None, None, None, None
        
        # Επανυπολογισμός της απόστασης και του χρόνου με μεγαλύτερη ακρίβεια
        recalculated_distance = 0.0
        recalculated_duration = 0.0
        
        # Διατρέχουμε τα σημεία της διαδρομής και υπολογίζουμε την ακριβή απόσταση και διάρκεια
        for i in range(len(geometry) - 1):
            p1_lon, p1_lat = geometry[i]
            p2_lon, p2_lat = geometry[i + 1]
            
            # Υπολογισμός απόστασης μεταξύ διαδοχικών σημείων σε km
            segment_distance = self.dijkstra.haversine(p1_lon, p1_lat, p2_lon, p2_lat)
            recalculated_distance += segment_distance
            
            # Υπολογισμός χρόνου με βάση τον τύπο του δρόμου
            # Εδώ κάνουμε απλοποίηση και υποθέτουμε μέση ταχύτητα 60 km/h για κύριους δρόμους
            # Αυτό βέβαια θα μπορούσε να είναι πιο ακριβές αν είχαμε τον τύπο δρόμου για κάθε τμήμα
            speed = 60.0  # km/h
            segment_duration = (segment_distance / speed) * 3600  # δευτερόλεπτα
            recalculated_duration += segment_duration
        
        # Αν έχουμε διαδρομή από τον Dijkstra, τη βελτιώνουμε οπτικά με το OSRM
        try:
            enhanced_geometry = self.osrm_helper.get_visualization_route(geometry)
            if enhanced_geometry and len(enhanced_geometry) > 1:
                print(f"Επιτυχής βελτίωση οπτικοποίησης διαδρομής από {len(geometry)} σε {len(enhanced_geometry)} σημεία")
                
                # Επανυπολογισμός της απόστασης και του χρόνου με τη βελτιωμένη γεωμετρία
                # Αυτό βοηθά την ακρίβεια καθώς το OSRM παρέχει περισσότερα σημεία που ακολουθούν πιο πιστά το δρόμο
                enhanced_distance = 0.0
                enhanced_duration = 0.0
                
                for i in range(len(enhanced_geometry) - 1):
                    p1_lon, p1_lat = enhanced_geometry[i]
                    p2_lon, p2_lat = enhanced_geometry[i + 1]
                    
                    segment_distance = self.dijkstra.haversine(p1_lon, p1_lat, p2_lon, p2_lat)
                    enhanced_distance += segment_distance
                    
                    # Εκτίμηση ταχύτητας με βάση τον τύπο της οδού
                    # Χρησιμοποιούμε μια μέση ταχύτητα 65 km/h για κύριους δρόμους και 35 km/h για αστικές περιοχές
                    if recalculated_distance > 20:  # Αν η συνολική απόσταση είναι μεγάλη, πιθανόν να περιλαμβάνει κύριους δρόμους
                        speed = 65.0
                    else:
                        speed = 35.0
                    
                    segment_duration = (segment_distance / speed) * 3600  # δευτερόλεπτα
                    enhanced_duration += segment_duration
                
                # Χρησιμοποιούμε το βελτιωμένο geometry, αλλά την απόσταση και διάρκεια 
                # την κρατάμε από τον δικό μας υπολογισμό για συνέπεια
                geometry = enhanced_geometry
                
                # Χρησιμοποιούμε την βελτιωμένη απόσταση και διάρκεια αν είναι λογικές
                # (όχι πολύ διαφορετικές από τις αρχικές)
                if enhanced_distance > 0 and abs(enhanced_distance - recalculated_distance) / recalculated_distance < 0.3:
                    recalculated_distance = enhanced_distance
                
                if enhanced_duration > 0 and abs(enhanced_duration - recalculated_duration) / recalculated_duration < 0.3:
                    recalculated_duration = enhanced_duration
        except Exception as e:
            print(f"Σφάλμα κατά τη βελτίωση οπτικοποίησης: {e}")
            # Διατηρούμε την αρχική διαδρομή από τον Dijkstra
            
        # Χρησιμοποιούμε τις επανυπολογισμένες τιμές αντί για τις αρχικές
        # Σημείωση: το recalculated_distance είναι ήδη σε χιλιόμετρα,
        # αλλά το frontend περιμένει τιμή σε μέτρα
        distance = recalculated_distance * 1000  # Μετατροπή από km σε μέτρα
        duration = recalculated_duration
            
        # αν όλα πήγαν καλά, επιστρέφουμε τα αποτελέσματα
        print(f"Επιτυχής εύρεση διαδρομής: {distance/1000:.2f}km, {duration/60:.1f} λεπτά")
        return geometry, distance, duration, steps
    
    def check_and_adjust_buffer(self, start_coords, end_coords):
        """
        Βελτιωμένος έλεγχος και προσαρμογή buffer για μεγάλες αποστάσεις στην Ελλάδα
        """
        # Υπολογισμός απόστασης σε ευθεία γραμμή
        start_lat, start_lon = start_coords[1], start_coords[0]
        end_lat, end_lon = end_coords[1], end_coords[0]
        distance_km = self.dijkstra.haversine(start_lon, start_lat, end_lon, end_lat)
        
        print(f"Απόσταση αφετηρίας-προορισμού: {distance_km:.2f} χλμ")
        
        # Ειδική διαχείριση για μεγάλες αποστάσεις (όπως Αίγιο-Πάτρα)
        if distance_km > 40:  # Πολύ μεγάλες αποστάσεις
            buffer = 0.5  # Μεγάλο buffer για να πιάσουμε όλους τους κύριους δρόμους
            print(f"Πολύ μεγάλη απόσταση (Αίγιο-Πάτρα τύπου), buffer: {buffer} μοίρες")
            self.osm_handler.buffer = buffer
        elif distance_km > 25:  # Μεγάλες αποστάσεις
            buffer = 0.3
            print(f"Μεγάλη απόσταση, buffer: {buffer} μοίρες")
            self.osm_handler.buffer = buffer
        elif distance_km > 15:  # Μεσαίες αποστάσεις
            buffer = 0.2
            print(f"Μεσαία απόσταση, buffer: {buffer} μοίρες")
            self.osm_handler.buffer = buffer
        else:  # Μικρές αποστάσεις
            self.osm_handler.buffer = 0.1
            print(f"Μικρή απόσταση, προεπιλεγμένο buffer: 0.1 μοίρες")
    
    def format_duration(self, seconds):
        """
        Μορφοποίηση της διάρκειας από δευτερόλεπτα σε κείμενο
        """
        # μετατροπή δευτερολέπτων σε λεπτά
        minutes = round(seconds / 60)
        
        if minutes < 60:
            return f"{minutes} λεπτά"
            
        # αν είναι πάνω από μια ώρα
        hours = minutes // 60
        remaining_minutes = minutes % 60
        
        # μορφοποίηση ανάλογα με τον αριθμό των ωρών
        if hours == 1:
            return f"{hours} ώρα και {remaining_minutes} λεπτά"
        else:
            return f"{hours} ώρες και {remaining_minutes} λεπτά"
    
    def format_steps(self, steps):
        """
        Μορφοποίηση των βημάτων για εμφάνιση στο frontend
        """
        if not steps:
            return []
            
        formatted_steps = []
        
        for i, step in enumerate(steps):
            # στρογγυλοποίηση απόστασης σε 2 δεκαδικά
            distance = round(step.get('distance', 0), 2)
            
            # μετατροπή διάρκειας από δευτερόλεπτα σε λεπτά
            duration = step.get('duration', 0)
            duration_minutes = round(duration / 60) if duration else 0
            
            # προσθήκη βήματος στη λίστα
            formatted_steps.append({
                'instruction': step.get('instruction', 'Continue'),
                'distance': distance,
                'duration': f"{duration_minutes} min"
            })
            
        return formatted_steps
    
    def _find_route_with_waypoints(self, start_coords, end_coords, waypoints, route_type):
        """Εύρεση διαδρομής με ενδιάμεσα σημεία (waypoints)"""
        print(f"Υπολογισμός διαδρομής με {len(waypoints)} waypoints")
        
        # Δημιουργία σειράς σημείων: start -> waypoints -> end
        all_points = [start_coords] + waypoints + [end_coords]
        
        # Υπολογισμός buffer βάσει όλων των σημείων
        self._adjust_buffer_for_multiple_points(all_points)
        
        # Λήψη οδικού δικτύου για όλα τα σημεία
        if not self._download_network_for_points(all_points):
            print("Αποτυχία στη λήψη οδικού δικτύου για waypoints")
            return None, None, None, None
        
        # Υπολογισμός διαδρομής ανά τμήμα
        combined_geometry = []
        total_distance = 0
        total_duration = 0
        combined_steps = []
        
        for i in range(len(all_points) - 1):
            segment_start = all_points[i]
            segment_end = all_points[i + 1]
            
            print(f"Τμήμα {i+1}: {segment_start} -> {segment_end}")
            
            # Υπολογισμός διαδρομής για αυτό το τμήμα
            geometry, distance, duration, steps = self.dijkstra.shortest_path(
                segment_start[1], segment_start[0],  # lat, lon
                segment_end[1], segment_end[0],
                force_connection=True
            )
            
            if not geometry:
                print(f"Δε βρέθηκε διαδρομή για τμήμα {i+1}")
                return None, None, None, None
            
            # Συνδυασμός αποτελεσμάτων (αποφυγή διπλών σημείων)
            if i == 0:
                combined_geometry.extend(geometry)
            else:
                combined_geometry.extend(geometry[1:])  # αποφυγή διπλού σημείου
            
            total_distance += distance
            total_duration += duration
            
            # Προσθήκη waypoint marker στα steps
            if i < len(waypoints):
                waypoint_step = {
                    'instruction': f'Φτάσατε στο waypoint {i+1}',
                    'distance': 0,
                    'duration': 0
                }
                steps.append(waypoint_step)
            
            combined_steps.extend(steps)
        
        print(f"Ολοκληρώθηκε διαδρομή με waypoints: {total_distance:.2f}m, {total_duration:.0f}s")
        
        return combined_geometry, total_distance, total_duration, combined_steps
    
    def _adjust_buffer_for_multiple_points(self, points):
        """Προσαρμογή buffer για πολλαπλά σημεία"""
        # Υπολογισμός bounding box για όλα τα σημεία
        lats = [point[1] for point in points]
        lons = [point[0] for point in points]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        # Υπολογισμός μέγιστης απόστασης
        max_distance = self.dijkstra.haversine(min_lon, min_lat, max_lon, max_lat)
        
        # Προσαρμογή buffer
        if max_distance > 50:
            self.osm_handler.buffer = 0.4
        elif max_distance > 30:
            self.osm_handler.buffer = 0.3
        elif max_distance > 15:
            self.osm_handler.buffer = 0.2
        else:
            self.osm_handler.buffer = 0.15
        
        print(f"Buffer προσαρμόστηκε σε {self.osm_handler.buffer} για max distance {max_distance:.2f} χλμ")
    
    def _download_network_for_points(self, points):
        """Λήψη οδικού δικτύου για όλα τα σημεία"""
        # Υπολογισμός bounding box
        lats = [point[1] for point in points]
        lons = [point[0] for point in points]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        # Χρήση των ακραίων σημείων για λήψη δικτύου
        return self.osm_handler.download_road_network([min_lon, min_lat], [max_lon, max_lat])
    
    def generate_route_alternatives(self, start_coords, end_coords, num_alternatives=2):
        """Δημιουργία εναλλακτικών διαδρομών"""
        print(f"Δημιουργία {num_alternatives} εναλλακτικών διαδρομών")
        
        alternatives = []
        
        # Κύρια διαδρομή
        main_route = self.find_route(start_coords, end_coords)
        if main_route[0] is not None:
            alternatives.append({
                'type': 'main',
                'geometry': main_route[0],
                'distance': main_route[1],
                'duration': main_route[2],
                'steps': main_route[3]
            })
        
        # Εναλλακτικές διαδρομές με τροποποιημένα παράμετρα
        for i in range(num_alternatives):
            # Τροποποίηση buffer για διαφορετικές διαδρομές
            original_buffer = self.osm_handler.buffer
            self.osm_handler.buffer = original_buffer * (1.2 + i * 0.3)
            
            alt_route = self.find_route(start_coords, end_coords)
            if alt_route[0] is not None:
                alternatives.append({
                    'type': f'alternative_{i+1}',
                    'geometry': alt_route[0],
                    'distance': alt_route[1],
                    'duration': alt_route[2],
                    'steps': alt_route[3]
                })
            
            # Επαναφορά buffer
            self.osm_handler.buffer = original_buffer
        
        return alternatives
