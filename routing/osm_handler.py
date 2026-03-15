import requests
import math
from .traffic_manager import TrafficManager

class OSMHandler:
    # Διαχείριση δεδομένων από το OpenStreetMap
    
    def __init__(self, dijkstra):
        # αναφορά στην κλάση dijkstra
        self.dijkstra = dijkstra
        self.buffer = 0.5  # αυξημένο buffer για καλύτερη κάλυψη του οδικού δικτύου
        self.traffic_manager = TrafficManager()  # Διαχειριστής κίνησης
        
    def download_road_network(self, start_coords, end_coords):
        """
        Κατεβάζει τα δεδομένα του οδικού δικτύου από το OpenStreetMap για την
        περιοχή γύρω από τις συντεταγμένες αρχής και τέλους
        """
        # Προετοιμασία του bounding box
        # Επέκταση της περιοχής γύρω από τα σημεία αρχής και τέλους (buffer σε μοίρες)
        # Τυπικά, 0.1 μοίρες είναι περίπου 11χλμ στον ισημερινό
        min_lat = min(start_coords[1], end_coords[1]) - self.buffer
        max_lat = max(start_coords[1], end_coords[1]) + self.buffer
        min_lon = min(start_coords[0], end_coords[0]) - self.buffer
        max_lon = max(start_coords[0], end_coords[0]) + self.buffer
        
        print(f"Λήψη οδικού δικτύου για περιοχή: {min_lat},{min_lon},{max_lat},{max_lon}")
        
        # Δημιουργία Overpass API query για οδικό δίκτυο
        # Λαμβάνουμε όλους τους δρόμους (ways) εντός του bounding box
        # που έχουν το tag highway και το τύπος δρόμου είναι κατάλληλος για οχήματα
        overpass_mirrors = [
            "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://lz4.overpass-api.de/api/interpreter",
        ]
        
        # Χειρισμός διαφορετικών τύπων δρόμων ανάλογα με την απόσταση
        distance = self.dijkstra.haversine(
            start_coords[0], start_coords[1],
            end_coords[0], end_coords[1]
        )
        
        # Βελτιωμένη επιλογή δρόμων για μεγάλες αποστάσεις στην Ελλάδα
        # Για αποστάσεις >30km (όπως Αίγιο-Πάτρα), εστιάζουμε σε κύριους δρόμους
        if distance > 30:
            # Μόνο κύριοι δρόμοι για μεγάλες αποστάσεις
            road_types = (
                "motorway|trunk|primary|secondary|"
                "motorway_link|trunk_link|primary_link|secondary_link"
            )
            print(f"Μεγάλη απόσταση ({distance:.1f}km) - Χρήση μόνο κύριων δρόμων")
        elif distance > 15:
            # Μεσαίες αποστάσεις - περισσότεροι τύποι
            road_types = (
                "motorway|trunk|primary|secondary|tertiary|"
                "motorway_link|trunk_link|primary_link|secondary_link|tertiary_link"
            )
            print(f"Μεσαία απόσταση ({distance:.1f}km) - Χρήση κύριων και δευτερευόντων δρόμων")
        else:
            # Μικρές αποστάσεις - όλοι οι τύποι
            road_types = (
                "motorway|trunk|primary|secondary|tertiary|unclassified|residential|"
                "motorway_link|trunk_link|primary_link|secondary_link|tertiary_link|"
                "living_street|service"
            )
            print(f"Μικρή απόσταση ({distance:.1f}km) - Χρήση όλων των τύπων δρόμων")
        
        max_nodes = 10000000  # Αύξηση ορίου για μεγάλες περιοχές

        # Βελτιωμένο query με μεγαλύτερο timeout για μεγάλες περιοχές
        timeout = 600 if distance > 30 else 300
        
        # Βελτιωμένο query που περιλαμβάνει όρια ταχύτητας και πρόσθετες πληροφορίες
        overpass_query = f"""
        [out:json][timeout:{timeout}][maxsize:2000000000];
        (
          way["highway"~"^({road_types})$"]({min_lat},{min_lon},{max_lat},{max_lon});
        );
        (._;>;);
        out body;
        """
        
        print(f"Λήψη δεδομένων με βελτιωμένες πληροφορίες (όρια ταχύτητας, τύπος δρόμου)...")

        http_timeout = 90  # δευτερόλεπτα για HTTP request timeout

        for mirror_index, overpass_url in enumerate(overpass_mirrors):
            try:
                print(f"Δοκιμή Overpass mirror {mirror_index + 1}/{len(overpass_mirrors)}: {overpass_url}")
                response = requests.post(
                    overpass_url,
                    data={"data": overpass_query},
                    timeout=http_timeout
                )

                if response.status_code != 200:
                    print(f"Σφάλμα από Overpass mirror {mirror_index + 1}: HTTP {response.status_code}")
                    print(response.text[:500])
                    continue  # Δοκιμή επόμενου mirror

                # Μετατροπή των δεδομένων από JSON σε Python objects
                data = response.json()

                # Ο αριθμός των στοιχείων που πήραμε
                elements = data.get("elements", [])
                print(f"Ελήφθησαν {len(elements)} στοιχεία από το OSM (mirror {mirror_index + 1})")

                if len(elements) == 0:
                    print(f"Mirror {mirror_index + 1} επέστρεψε κενά δεδομένα, δοκιμή επόμενου...")
                    continue

                # Μηδενισμός του γραφήματος (για επανάληψη της διαδικασίας)
                self.dijkstra.graph.clear()
                self.dijkstra.nodes.clear()

                # Επεξεργασία των στοιχείων και κατασκευή του γραφήματος
                return self._build_graph(elements)

            except requests.exceptions.Timeout:
                print(f"Timeout από Overpass mirror {mirror_index + 1}, δοκιμή επόμενου...")
                continue
            except Exception as e:
                print(f"Σφάλμα από Overpass mirror {mirror_index + 1}: {e}")
                continue

        print("αποτυχια στη λήψη οδικού δικτύου από όλα τα mirrors!")
        return False
    
    def _build_graph(self, elements):
        """
        Κατασκευή του γραφήματος από τα στοιχεία του OSM
        """
        for element in elements:
            if element['type'] == 'node':
                # Αποθηκεύουμε τις συντεταγμένες του κόμβου
                node_id = element['id']
                self.dijkstra.nodes[node_id] = (element['lat'], element['lon'])
        
        roads_processed = 0  # ένας μετρητής για αποσφαλμάτωση
        
        # Επεξεργαζόμαστε όλους τους δρόμους
        for element in elements:
            if element['type'] == 'way' and 'tags' in element and 'highway' in element['tags']:
                roads_processed += 1
                
                # Παίρνουμε τον τύπο του δρόμου και τα πραγματικά όρια ταχύτητας
                highway_type = element['tags']['highway']
                
                # Έλεγχος για πραγματικό όριο ταχύτητας από OSM
                actual_speed = self.extract_speed_limit(element['tags'])
                if actual_speed:
                    speed = actual_speed
                    print(f"Χρήση πραγματικού ορίου ταχύτητας: {speed} km/h για {highway_type}")
                else:
                    speed = self.get_speed_for_highway_type(highway_type)
                
                # Προσθήκη πληροφοριών για τον δρόμο
                road_info = {
                    'highway_type': highway_type,
                    'speed_limit': speed,
                    'is_urban': self.is_urban_area(element['tags']),
                    'surface': element['tags'].get('surface', 'unknown'),
                    'lanes': element['tags'].get('lanes', '1')
                }
                
                # Αγνοούμε μονοπάτια πεζών για δρομολόγηση αυτοκινήτου
                if highway_type in ['footway', 'path', 'steps', 'pedestrian']:
                    continue
                
                # Έλεγχος αν είναι μονόδρομος
                # oneway=yes: μόνο προς τη φορά των κόμβων
                # oneway=-1: μόνο ΑΝΤΙΘΕΤΑ της φοράς των κόμβων
                oneway_tag = element['tags'].get('oneway', 'no')
                if oneway_tag == 'yes':
                    oneway = 'forward'
                elif oneway_tag == '-1':
                    oneway = 'reverse'
                else:
                    oneway = 'no'
                
                # Εξετάζουμε κάθε ζεύγος συνδεδεμένων κόμβων
                nodes = element['nodes']
                for i in range(len(nodes) - 1):
                    # Παίρνω τους κόμβους αρχής και τέλους για αυτό το τμήμα δρόμου
                    from_node = nodes[i]
                    to_node = nodes[i + 1]
                    
                    # Υπολογισμός απόστασης με τον τύπο haversine
                    if from_node in self.dijkstra.nodes and to_node in self.dijkstra.nodes:
                        from_coords = self.dijkstra.nodes[from_node]
                        to_coords = self.dijkstra.nodes[to_node]
                        
                        # Υπολογίζουμε την απόσταση μεταξύ των δύο κόμβων
                        dist = self.dijkstra.haversine(
                            from_coords[1], from_coords[0], 
                            to_coords[1], to_coords[0]
                        )
                        
                        # Υπολογισμός χρόνου με όλους τους παράγοντες
                        base_time = (dist / speed) * 3600  # Βασικός χρόνος
                        
                        # Προσθήκη καθυστερήσεων βάσει τύπου δρόμου
                        realistic_time = self.calculate_realistic_time(base_time, road_info, dist)
                        
                        # Εφαρμογή συνθηκών κίνησης
                        time = self.traffic_manager.apply_traffic_conditions(
                            realistic_time, road_info, from_coords, to_coords
                        )
                        
                        # Προσθήκη ακμών στο γράφημα βάσει κατεύθυνσης μονόδρομου
                        edge_data = (to_node, dist, time, road_info)
                        reverse_edge_data = (from_node, dist, time, road_info)

                        if oneway == 'forward':
                            # Μόνο from→to
                            self.dijkstra.graph[from_node].append(edge_data)
                        elif oneway == 'reverse':
                            # Μόνο to→from (αντίθετη φορά)
                            self.dijkstra.graph[to_node].append(reverse_edge_data)
                        else:
                            # Αμφίδρομος δρόμος
                            self.dijkstra.graph[from_node].append(edge_data)
                            self.dijkstra.graph[to_node].append(reverse_edge_data)
        
        print(f"Κατασκευάστηκε γράφημα με {len(self.dijkstra.nodes)} κόμβους και {len(self.dijkstra.graph)} συνδεδεμένους κόμβους")
        print(f"Επεξεργάστηκα {roads_processed} δρόμους")

        # Κατασκευή spatial index για γρήγορη αναζήτηση κοντινότερου κόμβου
        self.dijkstra._build_spatial_index()

        # Επιστρέφουμε true αν καταφέραμε να φτιάξουμε ένα γράφημα με κόμβους
        return len(self.dijkstra.nodes) > 0 and len(self.dijkstra.graph) > 0
    
    def get_speed_for_highway_type(self, highway_type):
        """
        Επιστρέφει την εκτιμώμενη ταχύτητα σε km/h για διάφορους τύπους δρόμων
        """
        # Ορίζουμε τις ταχύτητες ανάλογα με τον τύπο δρόμου
        # Αυτές οι τιμές είναι προσεγγίσεις και δεν είναι ακριβείς
        speeds = {
            'motorway': 115,      # αυτοκινητόδρομος
            'motorway_link': 80,  # σύνδεση αυτοκινητοδρόμου
            'trunk': 90,          # κεντρική αρτηρία
            'trunk_link': 70,     # σύνδεση κεντρικής αρτηρίας
            'primary': 80,        # κύρια οδός
            'primary_link': 60,   # σύνδεση κύριας οδού
            'secondary': 70,      # δευτερεύουσα οδός
            'secondary_link': 50, # σύνδεση δευτερεύουσας οδού
            'tertiary': 60,       # τριτεύουσα οδός
            'tertiary_link': 40,  # σύνδεση τριτεύουσας οδού
            'unclassified': 40,   # μη ταξινομημένη οδός
            'residential': 30,    # οδός κατοικίας
            'living_street': 20,  # οδός ήπιας κυκλοφορίας
            'service': 20,        # οδός εξυπηρέτησης
            'track': 15,          # χωματόδρομος
            'path': 10,           # μονοπάτι
            'pedestrian': 5,      # πεζόδρομος
            'footway': 5,         # πεζόδρομος
            'cycleway': 15,       # ποδηλατόδρομος
            'bridleway': 10,      # μονοπάτι
            'steps': 3,           # σκάλες
            'corridor': 5,        # διάδρομος
            'platform': 5,        # πλατφόρμα
        }
        
        # Επιστρέφουμε την ταχύτητα για τον συγκεκριμένο τύπο δρόμου
        # αν δεν υπάρχει, επιστρέφουμε την προεπιλεγμένη τιμή 30 km/h
        return speeds.get(highway_type, 30)
    def extract_speed_limit(self, tags):
        """Εξαγωγή πραγματικών ορίων ταχύτητας από OSM tags"""
        # Έλεγχος για maxspeed tag
        if 'maxspeed' in tags:
            speed_str = tags['maxspeed']
            try:
                # Χειρισμός διαφορετικών μορφών (50, "50", "50 km/h", "50 mph")
                if speed_str.isdigit():
                    return int(speed_str)
                elif 'mph' in speed_str.lower():
                    # Μετατροπή από mph σε km/h
                    mph = int(''.join(filter(str.isdigit, speed_str)))
                    return int(mph * 1.60934)
                elif any(char.isdigit() for char in speed_str):
                    # Εξαγωγή αριθμών από string
                    return int(''.join(filter(str.isdigit, speed_str)))
            except (ValueError, TypeError):
                pass
        
        # Έλεγχος για ειδικές περιπτώσεις
        if 'zone:maxspeed' in tags:
            zone_speed = tags['zone:maxspeed']
            if zone_speed.isdigit():
                return int(zone_speed)
        
        return None
    
    def is_urban_area(self, tags):
        """Ελέγχει αν ο δρόμος βρίσκεται σε αστική περιοχή"""
        # Ενδείξεις αστικής περιοχής
        urban_indicators = [
            'residential', 'living_street', 'service', 'unclassified'
        ]
        
        highway_type = tags.get('highway', '')
        if highway_type in urban_indicators:
            return True
        
        # Έλεγχος για ειδικά tags
        if 'area' in tags and tags['area'] == 'yes':
            return True
        
        if 'place' in tags:
            return True
            
        # Έλεγχος για χαμηλά όρια ταχύτητας (ενδεικτικό αστικής περιοχής)
        speed_limit = self.extract_speed_limit(tags)
        if speed_limit and speed_limit <= 50:
            return True
            
        return False
    
    def calculate_realistic_time(self, base_time, road_info, distance_km):
        """Υπολογισμός ρεαλιστικού χρόνου με πρόσθετους παράγοντες"""
        adjusted_time = base_time
        highway_type = road_info['highway_type']
        is_urban = road_info['is_urban']
        
        # Παράγοντας καθυστέρησης βάσει τύπου δρόμου
        delay_factors = {
            'motorway': 1.0,        # Κανένας καθυστέρηση
            'trunk': 1.1,           # Μικρή καθυστέρηση
            'primary': 1.15,        # Κύριοι δρόμοι
            'secondary': 1.2,       # Δευτερεύοντες δρόμοι
            'tertiary': 1.25,       # Τριτεύοντες δρόμοι
            'residential': 1.4,     # Οικιστικοί δρόμοι
            'living_street': 1.6,   # Δρόμοι ήπιας κυκλοφορίας
            'service': 1.5,         # Δρόμοι εξυπηρέτησης
            'unclassified': 1.3     # Μη κατηγοριοποιημένοι
        }
        
        # Εφαρμογή παράγοντα καθυστέρησης
        delay_factor = delay_factors.get(highway_type, 1.2)
        adjusted_time *= delay_factor
        
        # Επιπλέον καθυστέρηση για αστικές περιοχές
        if is_urban:
            adjusted_time *= 1.3  # 30% επιπλέον καθυστέρηση
            
            # Προσθήκη χρόνου για φανάρια (εκτίμηση)
            # Κάθε 1km σε αστική περιοχή έχει ~2-3 φανάρια
            traffic_lights_delay = (distance_km * 2.5) * 20  # 20 δευτερόλεπτα ανά φανάρι
            adjusted_time += traffic_lights_delay
        
        # Πρόσθετες καθυστερήσεις βάσει επιφάνειας δρόμου
        surface = road_info.get('surface', 'unknown')
        if surface in ['unpaved', 'gravel', 'dirt', 'sand']:
            adjusted_time *= 1.5  # 50% επιπλέον καθυστέρηση
        elif surface in ['cobblestone', 'sett']:
            adjusted_time *= 1.2  # 20% επιπλέον καθυστέρηση
        
        return adjusted_time
    
    def get_traffic_summary(self):
        """Επιστροφή περίληψης συνθηκών κίνησης"""
        return self.traffic_manager.get_traffic_summary()
