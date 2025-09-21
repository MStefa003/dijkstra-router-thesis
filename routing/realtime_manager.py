import asyncio
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading
import uuid

class IncidentManager:
    """Διαχείριση incidents και real-time events"""
    
    def __init__(self):
        self.active_incidents = {}
        self.incident_types = [
            'accident', 'construction', 'traffic_jam', 'road_closure', 
            'weather', 'event', 'breakdown'
        ]
        self.severity_levels = ['low', 'medium', 'high', 'critical']
        
    def generate_random_incident(self, route_coords: List[Tuple[float, float]]) -> Dict:
        """Δημιουργία τυχαίου incident κατά μήκος της διαδρομής"""
        if not route_coords or len(route_coords) < 2:
            return None
            
        # Επιλογή τυχαίου σημείου στη διαδρομή
        point_index = random.randint(0, len(route_coords) - 1)
        incident_location = route_coords[point_index]
        
        incident = {
            'id': str(uuid.uuid4()),
            'type': random.choice(self.incident_types),
            'severity': random.choice(self.severity_levels),
            'location': {
                'lat': incident_location[1],
                'lon': incident_location[0]
            },
            'description': self._generate_description(),
            'delay_factor': self._calculate_delay_factor(),
            'start_time': datetime.now().isoformat(),
            'estimated_duration': random.randint(10, 120),  # λεπτά
            'affected_radius': random.uniform(0.5, 2.0),  # km
            'status': 'active'
        }
        
        self.active_incidents[incident['id']] = incident
        return incident
    
    def _generate_description(self) -> str:
        """Δημιουργία περιγραφής incident"""
        descriptions = {
            'accident': ['Τροχαίο ατύχημα', 'Σύγκρουση οχημάτων', 'Ατύχημα με τραυματίες'],
            'construction': ['Έργα οδοποιίας', 'Συντήρηση δρόμου', 'Ανακατασκευή'],
            'traffic_jam': ['Κυκλοφοριακή συμφόρηση', 'Βαριά κίνηση', 'Κίνηση στάση'],
            'road_closure': ['Κλείσιμο δρόμου', 'Προσωρινό κλείσιμο', 'Διακοπή κυκλοφορίας'],
            'weather': ['Δυσμενείς καιρικές συνθήκες', 'Βροχή', 'Ομίχλη'],
            'event': ['Εκδήλωση', 'Συγκέντρωση', 'Πορεία'],
            'breakdown': ['Βλάβη οχήματος', 'Πάνα φορτηγού', 'Μηχανική βλάβη']
        }
        
        incident_type = random.choice(list(descriptions.keys()))
        return random.choice(descriptions[incident_type])
    
    def _calculate_delay_factor(self) -> float:
        """Υπολογισμός παράγοντα καθυστέρησης"""
        base_factors = {
            'low': 1.2,
            'medium': 1.5,
            'high': 2.0,
            'critical': 3.0
        }
        return base_factors.get(random.choice(self.severity_levels), 1.5)
    
    def get_incidents_near_route(self, route_coords: List[Tuple[float, float]], 
                                radius_km: float = 1.0) -> List[Dict]:
        """Εύρεση incidents κοντά στη διαδρομή"""
        nearby_incidents = []
        
        for incident in self.active_incidents.values():
            incident_lat = incident['location']['lat']
            incident_lon = incident['location']['lon']
            
            # Έλεγχος αν το incident είναι κοντά στη διαδρομή
            for coord in route_coords:
                distance = self._haversine_distance(
                    coord[1], coord[0], incident_lat, incident_lon
                )
                if distance <= radius_km:
                    nearby_incidents.append(incident)
                    break
        
        return nearby_incidents
    
    def _haversine_distance(self, lat1, lon1, lat2, lon2) -> float:
        """Υπολογισμός απόστασης Haversine"""
        import math
        
        R = 6371  # Ακτίνα Γης σε km
        
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def resolve_incident(self, incident_id: str):
        """Επίλυση incident"""
        if incident_id in self.active_incidents:
            self.active_incidents[incident_id]['status'] = 'resolved'
            self.active_incidents[incident_id]['end_time'] = datetime.now().isoformat()
    
    def cleanup_old_incidents(self):
        """Καθαρισμός παλιών incidents"""
        current_time = datetime.now()
        to_remove = []
        
        for incident_id, incident in self.active_incidents.items():
            start_time = datetime.fromisoformat(incident['start_time'])
            duration = timedelta(minutes=incident['estimated_duration'])
            
            if current_time > start_time + duration:
                to_remove.append(incident_id)
        
        for incident_id in to_remove:
            del self.active_incidents[incident_id]


class RealtimeRouteManager:
    """Διαχείριση real-time route updates"""
    
    def __init__(self, route_manager):
        self.route_manager = route_manager
        self.incident_manager = IncidentManager()
        self.active_routes = {}  # route_id -> route_data
        self.websocket_clients = set()
        self.update_interval = 30  # δευτερόλεπτα
        self.running = False
        self.socketio_instance = None  # Θα οριστεί από το Flask app
        
    def start_monitoring(self):
        """Έναρξη real-time monitoring"""
        self.running = True
        # Ξεκινάμε το background thread για updates
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        print("🔄 Real-time monitoring ξεκίνησε")
    
    def stop_monitoring(self):
        """Διακοπή monitoring"""
        self.running = False
        print("⏹️ Real-time monitoring σταμάτησε")
    
    def register_route(self, route_id: str, route_data: Dict) -> str:
        """Καταχώρηση διαδρομής για monitoring"""
        self.active_routes[route_id] = {
            'route_data': route_data,
            'start_time': datetime.now(),
            'current_position': 0,  # Index στα coordinates
            'eta': route_data.get('duration', 0),
            'original_eta': route_data.get('duration', 0),
            'incidents': [],
            'status': 'active',
            'last_update': datetime.now()
        }
        
        print(f"📍 Καταχωρήθηκε διαδρομή {route_id} για real-time monitoring")
        return route_id
    
    def update_route_position(self, route_id: str, position_index: int):
        """Ενημέρωση θέσης στη διαδρομή"""
        if route_id in self.active_routes:
            route = self.active_routes[route_id]
            route['current_position'] = position_index
            route['last_update'] = datetime.now()
            
            # Υπολογισμός νέου ETA
            self._recalculate_eta(route_id)
    
    def _monitoring_loop(self):
        """Κύριος loop για monitoring"""
        while self.running:
            try:
                self._check_for_incidents()
                self._update_etas()
                self._cleanup_completed_routes()
                self._broadcast_updates()
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                print(f"❌ Σφάλμα στο monitoring loop: {e}")
                time.sleep(5)
    
    def _check_for_incidents(self):
        """Έλεγχος για νέα incidents"""
        for route_id, route_info in self.active_routes.items():
            if route_info['status'] != 'active':
                continue
                
            route_coords = route_info['route_data'].get('coordinates', [])
            
            # Πιθανότητα δημιουργίας incident (5% κάθε check)
            if random.random() < 0.05:
                incident = self.incident_manager.generate_random_incident(route_coords)
                if incident:
                    route_info['incidents'].append(incident)
                    print(f"🚨 Νέο incident: {incident['description']} στη διαδρομή {route_id}")
    
    def _recalculate_eta(self, route_id: str):
        """Επανυπολογισμός ETA"""
        if route_id not in self.active_routes:
            return
            
        route_info = self.active_routes[route_id]
        
        # Βασικός ETA
        remaining_time = route_info['original_eta']
        
        # Προσθήκη καθυστερήσεων από incidents
        for incident in route_info['incidents']:
            if incident['status'] == 'active':
                delay = incident['delay_factor'] * 300  # 5 λεπτά βάση
                remaining_time += delay
        
        # Προσθήκη τυχαίας παραλλαγής για ρεαλισμό
        variation = random.uniform(0.9, 1.1)
        remaining_time *= variation
        
        route_info['eta'] = max(0, remaining_time)
    
    def _update_etas(self):
        """Ενημέρωση όλων των ETA"""
        for route_id in list(self.active_routes.keys()):
            self._recalculate_eta(route_id)
    
    def _cleanup_completed_routes(self):
        """Καθαρισμός ολοκληρωμένων διαδρομών"""
        current_time = datetime.now()
        to_remove = []
        
        for route_id, route_info in self.active_routes.items():
            # Αφαίρεση διαδρομών που έχουν ολοκληρωθεί ή είναι πολύ παλιές
            elapsed = (current_time - route_info['start_time']).total_seconds()
            max_duration = route_info['original_eta'] * 2  # 2x του αρχικού ETA
            
            if elapsed > max_duration:
                to_remove.append(route_id)
        
        for route_id in to_remove:
            del self.active_routes[route_id]
            print(f"🏁 Διαδρομή {route_id} ολοκληρώθηκε")
        
        # Καθαρισμός παλιών incidents
        self.incident_manager.cleanup_old_incidents()
    
    def _broadcast_updates(self):
        """Αποστολή updates σε WebSocket clients"""
        if not self.websocket_clients or not self.active_routes:
            return
            
        # Αποστολή updates για κάθε ενεργή διαδρομή
        for route_id, route_info in self.active_routes.items():
            route_update = {
                'route_id': route_id,
                'eta': route_info['eta'],
                'original_eta': route_info['original_eta'],
                'incidents': route_info['incidents'],
                'status': route_info['status'],
                'delay_seconds': route_info['eta'] - route_info['original_eta'],
                'timestamp': datetime.now().isoformat()
            }
            
            # Εδώ θα στέλναμε το update στους WebSocket clients
            # Το socketio instance θα πρέπει να περαστεί από το Flask app
            if hasattr(self, 'socketio_instance') and self.socketio_instance:
                self.socketio_instance.emit('route_update', route_update, room=route_id)
            
        if self.active_routes:
            print(f"📡 Broadcasting updates για {len(self.active_routes)} διαδρομές")
    
    def get_route_status(self, route_id: str) -> Optional[Dict]:
        """Λήψη status διαδρομής"""
        if route_id not in self.active_routes:
            return None
            
        route_info = self.active_routes[route_id]
        return {
            'route_id': route_id,
            'status': route_info['status'],
            'eta': route_info['eta'],
            'original_eta': route_info['original_eta'],
            'delay_seconds': route_info['eta'] - route_info['original_eta'],
            'incidents': route_info['incidents'],
            'last_update': route_info['last_update'].isoformat()
        }
    
    def get_all_active_routes(self) -> Dict:
        """Λήψη όλων των ενεργών διαδρομών"""
        return {
            route_id: self.get_route_status(route_id) 
            for route_id in self.active_routes.keys()
        }
    
    def force_incident(self, route_id: str, incident_type: str = None) -> Dict:
        """Δημιουργία incident για testing"""
        if route_id not in self.active_routes:
            return None
            
        route_coords = self.active_routes[route_id]['route_data'].get('coordinates', [])
        incident = self.incident_manager.generate_random_incident(route_coords)
        
        if incident and incident_type:
            incident['type'] = incident_type
            incident['description'] = f"Forced {incident_type} incident"
        
        if incident:
            self.active_routes[route_id]['incidents'].append(incident)
            print(f"🧪 Forced incident: {incident['description']}")
        
        return incident
    
    def set_socketio_instance(self, socketio):
        """Ορισμός SocketIO instance για WebSocket communication"""
        self.socketio_instance = socketio
        print("🔌 SocketIO instance ορίστηκε στο RealtimeRouteManager")
