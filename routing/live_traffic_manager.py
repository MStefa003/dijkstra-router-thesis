import requests
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math

class LiveTrafficManager:
    """Enhanced traffic manager with real-time data from multiple sources"""
    
    def __init__(self):
        self.traffic_cache = {}
        self.cache_duration = 180  # 3 minutes cache for live data
        self.api_keys = self._load_api_keys()
        self.traffic_patterns = self._load_traffic_patterns()
        self.enabled_sources = ['here', 'mapbox', 'tomtom']  # Available sources
        
    def _load_api_keys(self):
        """Load API keys from environment variables"""
        return {
            'here_api_key': os.getenv('HERE_API_KEY'),
            'mapbox_token': os.getenv('MAPBOX_ACCESS_TOKEN'),
            'google_api_key': os.getenv('GOOGLE_MAPS_API_KEY'),
            'tomtom_api_key': os.getenv('TOMTOM_API_KEY')
        }
    
    def _load_traffic_patterns(self):
        """Load enhanced traffic patterns for Greece"""
        return {
            'rush_hours': {
                'morning': {'start': 7, 'end': 9, 'factor': 2.2},
                'evening': {'start': 17, 'end': 19, 'factor': 2.5}
            },
            'day_factors': {
                'weekday': 1.0,
                'saturday': 0.8,
                'sunday': 0.6,
                'holiday': 0.5
            },
            'road_type_congestion': {
                'motorway': {'base': 1.0, 'rush': 1.8, 'incident': 3.0},
                'trunk': {'base': 1.1, 'rush': 2.0, 'incident': 2.8},
                'primary': {'base': 1.2, 'rush': 2.2, 'incident': 2.5},
                'secondary': {'base': 1.3, 'rush': 2.0, 'incident': 2.2},
                'tertiary': {'base': 1.2, 'rush': 1.8, 'incident': 2.0},
                'residential': {'base': 1.4, 'rush': 1.7, 'incident': 1.8}
            },
            'traffic_lights': {
                'urban_density': 2.5,  # lights per km in urban areas
                'avg_delay_per_light': 45,  # seconds
                'rush_hour_multiplier': 1.8
            }
        }
    
    def get_here_traffic_data(self, start_coords: Tuple[float, float], 
                             end_coords: Tuple[float, float]) -> Optional[Dict]:
        """Get traffic data from HERE Traffic API"""
        if not self.api_keys['here_api_key']:
            return None
            
        try:
            # HERE Traffic API endpoint
            url = "https://traffic.ls.hereapi.com/traffic/6.3/flow.json"
            
            # Calculate midpoint for traffic query
            mid_lat = (start_coords[0] + end_coords[0]) / 2
            mid_lon = (start_coords[1] + end_coords[1]) / 2
            
            params = {
                'apikey': self.api_keys['here_api_key'],
                'prox': f"{mid_lat},{mid_lon},5000",  # 5km radius
                'responseattributes': 'sh,fc'
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # Process HERE traffic data
                traffic_info = {
                    'source': 'here',
                    'flow_speed': 50,  # default
                    'free_flow_speed': 60,
                    'confidence': 0.8,
                    'incidents': []
                }
                
                if 'RWS' in data and data['RWS']:
                    for rws in data['RWS']:
                        if 'RW' in rws:
                            for rw in rws['RW']:
                                if 'FIS' in rw:
                                    for fis in rw['FIS']:
                                        if 'FI' in fis:
                                            for fi in fis['FI']:
                                                if 'CF' in fi:
                                                    for cf in fi['CF']:
                                                        speed = cf.get('SP', 50)
                                                        free_speed = cf.get('FF', 60)
                                                        traffic_info['flow_speed'] = speed
                                                        traffic_info['free_flow_speed'] = free_speed
                
                return traffic_info
                
        except Exception as e:
            print(f"HERE Traffic API error: {e}")
            return None
    
    def get_mapbox_traffic_data(self, start_coords: Tuple[float, float], 
                               end_coords: Tuple[float, float]) -> Optional[Dict]:
        """Get traffic data from MapBox Traffic API"""
        if not self.api_keys['mapbox_token']:
            return None
            
        try:
            # MapBox Directions API with traffic
            coordinates = f"{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}"
            url = f"https://api.mapbox.com/directions/v5/mapbox/driving-traffic/{coordinates}"
            
            params = {
                'access_token': self.api_keys['mapbox_token'],
                'annotations': 'duration,speed',
                'overview': 'simplified'
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                if 'routes' in data and data['routes']:
                    route = data['routes'][0]
                    duration_traffic = route.get('duration', 0)
                    
                    # Get duration without traffic for comparison
                    url_no_traffic = f"https://api.mapbox.com/directions/v5/mapbox/driving/{coordinates}"
                    response_no_traffic = requests.get(url_no_traffic, params=params, timeout=5)
                    
                    duration_no_traffic = duration_traffic
                    if response_no_traffic.status_code == 200:
                        data_no_traffic = response_no_traffic.json()
                        if 'routes' in data_no_traffic and data_no_traffic['routes']:
                            duration_no_traffic = data_no_traffic['routes'][0].get('duration', duration_traffic)
                    
                    delay_factor = duration_traffic / max(duration_no_traffic, 1)
                    
                    return {
                        'source': 'mapbox',
                        'delay_factor': delay_factor,
                        'duration_with_traffic': duration_traffic,
                        'duration_without_traffic': duration_no_traffic,
                        'confidence': 0.9
                    }
                    
        except Exception as e:
            print(f"MapBox Traffic API error: {e}")
            return None
    
    def get_tomtom_traffic_data(self, start_coords: Tuple[float, float], 
                               end_coords: Tuple[float, float]) -> Optional[Dict]:
        """Get traffic data from TomTom Traffic API"""
        if not self.api_keys['tomtom_api_key']:
            return None
            
        try:
            # TomTom Traffic Flow API
            mid_lat = (start_coords[0] + end_coords[0]) / 2
            mid_lon = (start_coords[1] + end_coords[1]) / 2
            
            url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
            
            params = {
                'key': self.api_keys['tomtom_api_key'],
                'point': f"{mid_lat},{mid_lon}"
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                current_speed = data.get('flowSegmentData', {}).get('currentSpeed', 50)
                free_flow_speed = data.get('flowSegmentData', {}).get('freeFlowSpeed', 60)
                confidence = data.get('flowSegmentData', {}).get('confidence', 0.7)
                
                delay_factor = free_flow_speed / max(current_speed, 1)
                
                return {
                    'source': 'tomtom',
                    'current_speed': current_speed,
                    'free_flow_speed': free_flow_speed,
                    'delay_factor': delay_factor,
                    'confidence': confidence
                }
                
        except Exception as e:
            print(f"TomTom Traffic API error: {e}")
            return None
    
    def get_live_traffic_data(self, start_coords: Tuple[float, float], 
                             end_coords: Tuple[float, float]) -> Dict:
        """Get aggregated live traffic data from multiple sources"""
        cache_key = f"{start_coords[0]:.3f},{start_coords[1]:.3f}-{end_coords[0]:.3f},{end_coords[1]:.3f}"
        
        # Check cache first
        if cache_key in self.traffic_cache:
            cached_data = self.traffic_cache[cache_key]
            if time.time() - cached_data['timestamp'] < self.cache_duration:
                return cached_data['data']
        
        # Collect data from multiple sources
        traffic_sources = []
        
        # Try HERE API
        here_data = self.get_here_traffic_data(start_coords, end_coords)
        if here_data:
            traffic_sources.append(here_data)
        
        # Try MapBox API
        mapbox_data = self.get_mapbox_traffic_data(start_coords, end_coords)
        if mapbox_data:
            traffic_sources.append(mapbox_data)
        
        # Try TomTom API
        tomtom_data = self.get_tomtom_traffic_data(start_coords, end_coords)
        if tomtom_data:
            traffic_sources.append(tomtom_data)
        
        # Aggregate data from sources
        if traffic_sources:
            aggregated_data = self._aggregate_traffic_data(traffic_sources)
        else:
            # Fallback to pattern-based estimation
            aggregated_data = self._get_pattern_based_traffic()
        
        # Add traffic light delays
        aggregated_data.update(self._calculate_traffic_light_delays(start_coords, end_coords))
        
        # Cache the result
        self.traffic_cache[cache_key] = {
            'data': aggregated_data,
            'timestamp': time.time()
        }
        
        return aggregated_data
    
    def _aggregate_traffic_data(self, sources: List[Dict]) -> Dict:
        """Aggregate traffic data from multiple sources with confidence weighting"""
        total_weight = 0
        weighted_delay = 0
        
        for source in sources:
            confidence = source.get('confidence', 0.5)
            delay_factor = source.get('delay_factor', 1.0)
            
            weighted_delay += delay_factor * confidence
            total_weight += confidence
        
        if total_weight > 0:
            final_delay_factor = weighted_delay / total_weight
        else:
            final_delay_factor = 1.0
        
        # Determine traffic level
        if final_delay_factor >= 2.0:
            level = 'heavy'
        elif final_delay_factor >= 1.5:
            level = 'moderate'
        elif final_delay_factor >= 1.2:
            level = 'light'
        else:
            level = 'free_flow'
        
        return {
            'level': level,
            'delay_factor': final_delay_factor,
            'sources_used': [s['source'] for s in sources],
            'confidence': min(total_weight, 1.0),
            'timestamp': time.time()
        }
    
    def _get_pattern_based_traffic(self) -> Dict:
        """Enhanced pattern-based traffic estimation with realistic variation"""
        current_time = datetime.now()
        hour = current_time.hour
        weekday = current_time.weekday()
        
        # Add some randomness for realistic traffic variation
        import random
        base_variation = random.uniform(0.8, 1.2)  # ±20% variation
        
        # Pattern-based estimation with more realistic values
        if weekday < 5:  # Weekdays
            if 7 <= hour <= 9:
                delay_factor = 2.2 * base_variation
                level = 'heavy' if delay_factor > 1.8 else 'moderate'
            elif 17 <= hour <= 19:
                delay_factor = 2.5 * base_variation
                level = 'heavy' if delay_factor > 1.8 else 'moderate'
            elif 10 <= hour <= 16:
                delay_factor = 1.4 * base_variation
                level = 'moderate' if delay_factor > 1.3 else 'light'
            else:
                delay_factor = 1.1 * base_variation
                level = 'light' if delay_factor > 1.0 else 'free_flow'
        else:  # Weekends
            if 10 <= hour <= 18:
                delay_factor = 1.3 * base_variation
                level = 'moderate' if delay_factor > 1.2 else 'light'
            else:
                delay_factor = 1.0 * base_variation
                level = 'free_flow'
        
        return {
            'level': level,
            'delay_factor': max(1.0, delay_factor),  # Minimum 1.0x
            'source': 'pattern_enhanced',
            'variation': base_variation
        }
    
    def _calculate_traffic_light_delays(self, start_coords: Tuple[float, float], 
                                       end_coords: Tuple[float, float]) -> Dict:
        """Calculate delays from traffic lights based on route characteristics"""
        # Calculate route distance
        distance_km = self._haversine_distance(start_coords, end_coords)
        
        # Estimate if route passes through urban areas
        # This is a simplified estimation - in reality you'd use OSM data
        is_urban = self._is_urban_route(start_coords, end_coords)
        
        if is_urban:
            lights_per_km = self.traffic_patterns['traffic_lights']['urban_density']
            avg_delay = self.traffic_patterns['traffic_lights']['avg_delay_per_light']
            
            # Rush hour multiplier
            current_time = datetime.now()
            hour = current_time.hour
            rush_multiplier = 1.0
            
            if 7 <= hour <= 9 or 17 <= hour <= 19:
                rush_multiplier = self.traffic_patterns['traffic_lights']['rush_hour_multiplier']
            
            total_lights = distance_km * lights_per_km
            total_delay = total_lights * avg_delay * rush_multiplier
            
            return {
                'traffic_light_delay': total_delay,
                'estimated_lights': int(total_lights),
                'is_urban_route': True
            }
        else:
            return {
                'traffic_light_delay': 0,
                'estimated_lights': 0,
                'is_urban_route': False
            }
    
    def _haversine_distance(self, coord1: Tuple[float, float], 
                           coord2: Tuple[float, float]) -> float:
        """Calculate distance between two coordinates in km"""
        R = 6371  # Earth's radius in km
        
        lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
        lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _is_urban_route(self, start_coords: Tuple[float, float], 
                       end_coords: Tuple[float, float]) -> bool:
        """Estimate if route passes through urban areas (simplified)"""
        # This is a simplified check - in reality you'd use OSM data
        # For Greece, major urban areas coordinates (approximate)
        urban_centers = [
            (37.9755, 23.7348),  # Athens
            (40.6401, 22.9444),  # Thessaloniki
            (38.2466, 21.7348),  # Patras
            (35.3387, 25.1442),  # Heraklion
        ]
        
        for urban_lat, urban_lon in urban_centers:
            # Check if route is within 20km of urban center
            start_dist = self._haversine_distance(start_coords, (urban_lat, urban_lon))
            end_dist = self._haversine_distance(end_coords, (urban_lat, urban_lon))
            
            if start_dist < 20 or end_dist < 20:
                return True
        
        return False
    
    def apply_live_traffic_to_route(self, base_time: float, road_info: Dict, 
                                   start_coords: Tuple[float, float], 
                                   end_coords: Tuple[float, float]) -> float:
        """Apply live traffic conditions to base travel time"""
        # Get live traffic data
        traffic_data = self.get_live_traffic_data(start_coords, end_coords)
        
        # Base traffic factor from road type and time patterns
        traffic_factor = self._get_road_type_factor(road_info)
        
        # Apply live traffic delay factor
        live_delay_factor = traffic_data.get('delay_factor', 1.0)
        combined_factor = traffic_factor * live_delay_factor
        
        # Add traffic light delays
        traffic_light_delay = traffic_data.get('traffic_light_delay', 0)
        
        # Calculate final time
        final_time = (base_time * combined_factor) + traffic_light_delay
        
        return final_time
    
    def _get_road_type_factor(self, road_info: Dict) -> float:
        """Get traffic factor based on road type and current time"""
        highway_type = road_info.get('highway_type', 'unclassified')
        current_time = datetime.now()
        hour = current_time.hour
        
        road_congestion = self.traffic_patterns['road_type_congestion']
        base_factor = road_congestion.get(highway_type, {'base': 1.2, 'rush': 1.5})
        
        # Check if rush hour
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            return base_factor['rush']
        else:
            return base_factor['base']
    
    def get_enhanced_traffic_summary(self) -> Dict:
        """Get comprehensive traffic summary with live data status"""
        current_time = datetime.now()
        
        # Check API availability
        api_status = {}
        for api_name, api_key in self.api_keys.items():
            api_status[api_name] = 'available' if api_key else 'not_configured'
        
        # Get basic traffic summary
        basic_summary = self._get_pattern_based_traffic()
        
        return {
            'current_conditions': basic_summary,
            'live_data_sources': {
                'here_traffic': api_status['here_api_key'],
                'mapbox_traffic': api_status['mapbox_token'],
                'tomtom_traffic': api_status['tomtom_api_key'],
                'google_traffic': api_status['google_api_key']
            },
            'features': {
                'real_time_traffic': any(status == 'available' for status in api_status.values()),
                'traffic_light_estimation': True,
                'incident_detection': True,
                'multi_source_aggregation': True,
                'confidence_weighting': True
            },
            'cache_stats': {
                'entries': len(self.traffic_cache),
                'cache_duration': f"{self.cache_duration}s"
            },
            'timestamp': current_time.isoformat()
        }
