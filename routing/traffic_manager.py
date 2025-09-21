import requests
import time
from datetime import datetime, timedelta
import json

class TrafficManager:
    """Διαχείριση δεδομένων κίνησης και real-time traffic conditions"""
    
    def __init__(self):
        self.traffic_cache = {}
        self.cache_duration = 300  # 5 λεπτά cache
        self.traffic_patterns = self._load_traffic_patterns()
        
    def _load_traffic_patterns(self):
        """Φόρτωση προκαθορισμένων patterns κίνησης για την Ελλάδα"""
        return {
            'rush_hours': {
                'morning': {'start': 7, 'end': 9, 'factor': 1.8},
                'evening': {'start': 17, 'end': 19, 'factor': 2.0}
            },
            'day_factors': {
                'weekday': 1.0,
                'saturday': 0.8,
                'sunday': 0.6
            },
            'road_type_congestion': {
                'motorway': {'base': 1.0, 'rush': 1.5},
                'trunk': {'base': 1.1, 'rush': 1.8},
                'primary': {'base': 1.2, 'rush': 2.0},
                'secondary': {'base': 1.3, 'rush': 1.9},
                'tertiary': {'base': 1.2, 'rush': 1.7},
                'residential': {'base': 1.4, 'rush': 1.6},
                'living_street': {'base': 1.5, 'rush': 1.5}
            }
        }
    
    def get_traffic_factor(self, road_info, current_time=None):
        """Υπολογισμός παράγοντα κίνησης βάσει ώρας και τύπου δρόμου"""
        if current_time is None:
            current_time = datetime.now()
        
        highway_type = road_info.get('highway_type', 'unclassified')
        is_urban = road_info.get('is_urban', False)
        
        # Βασικός παράγοντας βάσει τύπου δρόμου
        road_congestion = self.traffic_patterns['road_type_congestion']
        base_factor = road_congestion.get(highway_type, {'base': 1.2, 'rush': 1.5})
        
        # Έλεγχος αν είναι ώρα αιχμής
        hour = current_time.hour
        is_rush_hour = False
        rush_factor = 1.0
        
        # Πρωινή ώρα αιχμής
        morning_rush = self.traffic_patterns['rush_hours']['morning']
        if morning_rush['start'] <= hour <= morning_rush['end']:
            is_rush_hour = True
            rush_factor = morning_rush['factor']
        
        # Απογευματινή ώρα αιχμής
        evening_rush = self.traffic_patterns['rush_hours']['evening']
        if evening_rush['start'] <= hour <= evening_rush['end']:
            is_rush_hour = True
            rush_factor = evening_rush['factor']
        
        # Παράγοντας ημέρας εβδομάδας
        weekday = current_time.weekday()  # 0=Δευτέρα, 6=Κυριακή
        if weekday < 5:  # Δευτέρα-Παρασκευή
            day_factor = self.traffic_patterns['day_factors']['weekday']
        elif weekday == 5:  # Σάββατο
            day_factor = self.traffic_patterns['day_factors']['saturday']
        else:  # Κυριακή
            day_factor = self.traffic_patterns['day_factors']['sunday']
        
        # Υπολογισμός τελικού παράγοντα
        if is_rush_hour:
            traffic_factor = base_factor['rush'] * rush_factor * day_factor
        else:
            traffic_factor = base_factor['base'] * day_factor
        
        # Επιπλέον καθυστέρηση για αστικές περιοχές
        if is_urban:
            traffic_factor *= 1.2
        
        return min(traffic_factor, 3.0)  # Όριο στο 3x της κανονικής ταχύτητας
    
    def get_real_time_traffic(self, start_coords, end_coords):
        """Προσπάθεια λήψης real-time traffic data (mock implementation)"""
        # Αυτή είναι μια mock implementation
        # Σε πραγματική εφαρμογή θα χρησιμοποιούσαμε APIs όπως:
        # - Google Maps Traffic API
        # - HERE Traffic API
        # - TomTom Traffic API
        # - OpenTraffic
        
        cache_key = f"{start_coords[0]:.3f},{start_coords[1]:.3f}-{end_coords[0]:.3f},{end_coords[1]:.3f}"
        
        # Έλεγχος cache
        if cache_key in self.traffic_cache:
            cached_data = self.traffic_cache[cache_key]
            if time.time() - cached_data['timestamp'] < self.cache_duration:
                return cached_data['data']
        
        # Προσομοίωση real-time traffic data
        current_time = datetime.now()
        hour = current_time.hour
        
        # Βασική προσομοίωση κίνησης
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            # Ώρες αιχμής
            traffic_level = 'heavy'
            delay_factor = 1.8
        elif 10 <= hour <= 16:
            # Μεσημέρι
            traffic_level = 'moderate'
            delay_factor = 1.3
        elif 20 <= hour <= 23:
            # Βράδυ
            traffic_level = 'light'
            delay_factor = 1.1
        else:
            # Νύχτα/Πρωί
            traffic_level = 'free_flow'
            delay_factor = 1.0
        
        traffic_data = {
            'level': traffic_level,
            'delay_factor': delay_factor,
            'incidents': [],  # Θα μπορούσε να περιλαμβάνει ατυχήματα, έργα κλπ
            'timestamp': time.time()
        }
        
        # Αποθήκευση στο cache
        self.traffic_cache[cache_key] = {
            'data': traffic_data,
            'timestamp': time.time()
        }
        
        return traffic_data
    
    def apply_traffic_conditions(self, base_time, road_info, start_coords=None, end_coords=None):
        """Εφαρμογή συνθηκών κίνησης στον βασικό χρόνο"""
        # Παράγοντας κίνησης βάσει ώρας και τύπου δρόμου
        traffic_factor = self.get_traffic_factor(road_info)
        
        # Real-time traffic data (αν διατίθεται)
        if start_coords and end_coords:
            real_time_data = self.get_real_time_traffic(start_coords, end_coords)
            traffic_factor *= real_time_data['delay_factor']
        
        return base_time * traffic_factor
    
    def get_traffic_summary(self):
        """Επιστρέφει περίληψη των τρεχουσών συνθηκών κίνησης"""
        current_time = datetime.now()
        hour = current_time.hour
        weekday = current_time.weekday()
        
        # Καθορισμός γενικής κατάστασης κίνησης
        if weekday < 5:  # Εργάσιμες ημέρες
            if 7 <= hour <= 9:
                status = "Πρωινή ώρα αιχμής - Βαριά κίνηση"
                color = "red"
            elif 17 <= hour <= 19:
                status = "Απογευματινή ώρα αιχμής - Πολύ βαριά κίνηση"
                color = "red"
            elif 10 <= hour <= 16:
                status = "Μέτρια κίνηση"
                color = "yellow"
            else:
                status = "Ελαφριά κίνηση"
                color = "green"
        else:  # Σαββατοκύριακο
            if 10 <= hour <= 18:
                status = "Μέτρια κίνηση (Σαββατοκύριακο)"
                color = "yellow"
            else:
                status = "Ελαφριά κίνηση"
                color = "green"
        
        return {
            'status': status,
            'color': color,
            'current_time': current_time.strftime("%H:%M"),
            'day_type': 'Εργάσιμη' if weekday < 5 else 'Σαββατοκύριακο',
            'cache_entries': len(self.traffic_cache)
        }
    
    def clear_cache(self):
        """Καθαρισμός cache κίνησης"""
        self.traffic_cache.clear()
        print("Traffic cache καθαρίστηκε")
    
    def get_incident_delays(self, road_type, distance_km):
        """Υπολογισμός καθυστερήσεων από incidents (ατυχήματα, έργα κλπ)"""
        # Προσομοίωση incidents
        # Σε πραγματική εφαρμογή θα παίρναμε δεδομένα από traffic APIs
        
        incident_probability = {
            'motorway': 0.02,    # 2% πιθανότητα ανά km
            'trunk': 0.015,      # 1.5% πιθανότητα ανά km
            'primary': 0.01,     # 1% πιθανότητα ανά km
            'secondary': 0.008,  # 0.8% πιθανότητα ανά km
            'residential': 0.005 # 0.5% πιθανότητα ανά km
        }
        
        prob = incident_probability.get(road_type, 0.01)
        
        # Απλή προσομοίωση
        import random
        if random.random() < prob * distance_km:
            # Υπάρχει incident
            delay_minutes = random.randint(5, 20)  # 5-20 λεπτά καθυστέρηση
            return delay_minutes * 60  # Επιστροφή σε δευτερόλεπτα
        
        return 0
