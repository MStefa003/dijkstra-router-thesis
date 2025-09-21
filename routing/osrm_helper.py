import requests

class OSRMHelper:
    # μόνο για οπτικοποίηση διαδρομών ΧΩΡΙΣ υπολογισμό διαδρομών
    
    def __init__(self):
        # Χρησιμοποιούμε το δημόσιο API του OSRM project
        self.base_url = "http://router.project-osrm.org"
        
    def get_visualization_route(self, coordinates):
        # Βελτιώνει την οπτικοποίηση μιας διαδρομής με βάση τα σημεία που δίνονται
        """
        Λαμβάνει μια λίστα συντεταγμένων [lon, lat] και επιστρέφει μια βελτιωμένη
        διαδρομή που ακολουθεί ακριβώς το οδικό δίκτυο για οπτικοποίηση.
        
        Αυτή η μέθοδος ΔΕΝ υπολογίζει τη διαδρομή, απλά χρησιμοποιεί τα σημεία που
        έχει ήδη υπολογίσει ο δικός μας αλγόριθμος Dijkstra.
        """
        if not coordinates or len(coordinates) < 2:
            print("Δεν υπάρχουν επαρκείς συντεταγμένες για βελτίωση οπτικοποίησης")
            return coordinates
            
        # Για μεγάλα σύνολα σημείων, διατηρούμε μόνο ένα υποσύνολο για να μην υπερφορτώσουμε το API
        # Επιλέγουμε μέχρι 100 σημεία, φροντίζοντας πάντα να συμπεριλάβουμε το πρώτο και το τελευταίο
        if len(coordinates) > 100:
            step = len(coordinates) // 100
            reduced_coords = [coordinates[0]] + [coordinates[i] for i in range(step, len(coordinates)-1, step)] + [coordinates[-1]]
            coordinates = reduced_coords
            
        # Μετατροπή συντεταγμένων σε μορφή που απαιτεί το API (lon,lat;lon,lat;...)
        coords_str = ";".join([f"{coord[0]},{coord[1]}" for coord in coordinates])
        
        # Δημιουργία του URL για το OSRM Match API (για την καλύτερη προσαρμογή στο οδικό δίκτυο)
        url = f"{self.base_url}/match/v1/driving/{coords_str}?overview=full&geometries=geojson"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                print(f"Σφάλμα στη βελτιστοποίηση οπτικοποίησης: {response.status_code}")
                return coordinates
                
            data = response.json()
            
            # Έλεγχος αν υπάρχουν αποτελέσματα
            if 'matchings' not in data or not data['matchings']:
                print("Δεν βρέθηκαν βελτιωμένες συντεταγμένες")
                return coordinates
                
            # Λαμβάνουμε τις συντεταγμένες από το πρώτο matching
            # Οι συντεταγμένες είναι ήδη σε μορφή [lon, lat]
            enhanced_coords = data['matchings'][0]['geometry']['coordinates']
            
            if not enhanced_coords:
                return coordinates
                
            print(f"Επιτυχής βελτίωση οπτικοποίησης: {len(coordinates)} σημεία → {len(enhanced_coords)} σημεία")
            return enhanced_coords
            
        except Exception as e:
            print(f"Σφάλμα κατά την επικοινωνία με το OSRM API: {e}")
            return coordinates  # Επιστρέφουμε τις αρχικές συντεταγμένες σε περίπτωση σφάλματος
            
    def get_route_visualization(self, start_coords, end_coords, via_points=None):
        """
        Εναλλακτική μέθοδος που χρησιμοποιεί το OSRM Route API για να δημιουργήσει
        μια συνεχή διαδρομή μεταξύ αφετηρίας και προορισμού, προαιρετικά περνώντας
        από συγκεκριμένα σημεία που έχει υπολογίσει ο αλγόριθμος Dijkstra.
        """
        # Αρχικοποίηση της λίστας σημείων με αφετηρία και προορισμό
        all_points = [start_coords]
        
        # Προσθήκη ενδιάμεσων σημείων εάν υπάρχουν
        if via_points and len(via_points) > 0:
            all_points.extend(via_points)
            
        all_points.append(end_coords)
        
        # Μετατροπή σε string για το API
        coords_str = ";".join([f"{coord[0]},{coord[1]}" for coord in all_points])
        
        # Δημιουργία του URL για το OSRM Route API
        url = f"{self.base_url}/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                print(f"Σφάλμα στη δημιουργία διαδρομής: {response.status_code}")
                return all_points
                
            data = response.json()
            
            # Έλεγχος αν υπάρχουν αποτελέσματα
            if 'routes' not in data or not data['routes']:
                print("Δεν βρέθηκε διαδρομή")
                return all_points
                
            # Λαμβάνουμε τις συντεταγμένες από την πρώτη διαδρομή
            route_coords = data['routes'][0]['geometry']['coordinates']
            
            if not route_coords:
                return all_points
                
            print(f"Επιτυχής δημιουργία οπτικοποίησης διαδρομής με {len(route_coords)} σημεία")
            return route_coords
            
        except Exception as e:
            print(f"Σφάλμα κατά την επικοινωνία με το OSRM API: {e}")
            return all_points  # Επιστρέφουμε τα αρχικά σημεία σε περίπτωση σφάλματος
