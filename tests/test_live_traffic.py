#!/usr/bin/env python3
"""
Test script για live traffic integration
Δείχνει πώς να χρησιμοποιήσετε τα νέα live traffic features
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:5000"

def test_live_traffic_status():
    """Test live traffic API status"""
    print("🔍 Checking live traffic API status...")
    
    try:
        response = requests.get(f"{BASE_URL}/live_traffic_status")
        if response.status_code == 200:
            data = response.json()
            print("✅ Live Traffic Status:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Connection error: {e}")

def test_route_with_live_traffic():
    """Test route calculation with live traffic data"""
    print("\n🚗 Testing route with live traffic...")
    
    # Test route: Athens to Patras (example coordinates)
    route_data = {
        "start": [23.7275, 37.9755],  # Athens [lon, lat]
        "end": [21.7348, 38.2466],    # Patras [lon, lat]
        "type": "driving",
        "use_live_data": True
    }
    
    try:
        print(f"📍 Route: Athens → Patras")
        print(f"🔄 Calculating with live traffic data...")
        
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/route_with_live_traffic", 
            json=route_data,
            timeout=30
        )
        calc_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                route = data['route']
                traffic_analysis = data['live_traffic_analysis']
                
                print("✅ Route calculated successfully!")
                print(f"📏 Distance: {route['distance_km']} km")
                print(f"⏱️  Duration with traffic: {route['duration']}")
                print(f"⏱️  Original duration: {route['original_duration']}")
                print(f"🚦 Traffic delay: {route['traffic_delay_seconds']}s ({route['delay_percentage']}%)")
                print(f"🧮 Calculation time: {calc_time:.2f}s")
                
                print("\n📊 Live Traffic Analysis:")
                print(f"   Data available: {traffic_analysis['data_available']}")
                print(f"   Sources used: {traffic_analysis['sources_used']}")
                print(f"   Confidence: {traffic_analysis['confidence']:.1%}")
                print(f"   Traffic level: {traffic_analysis['traffic_level']}")
                print(f"   Delay factor: {traffic_analysis['delay_factor']:.2f}x")
                print(f"   Traffic lights: {traffic_analysis['estimated_lights']}")
                print(f"   Urban route: {traffic_analysis['is_urban_route']}")
                
            else:
                print(f"❌ Route calculation failed: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_comparison_with_without_traffic():
    """Compare route times with and without live traffic"""
    print("\n📊 Comparing routes with/without live traffic...")
    
    route_data = {
        "start": [23.7275, 37.9755],  # Athens
        "end": [21.7348, 38.2466],    # Patras
        "type": "driving"
    }
    
    results = {}
    
    # Test without live traffic
    print("🔄 Calculating without live traffic...")
    route_data["use_live_data"] = False
    try:
        response = requests.post(f"{BASE_URL}/route_with_live_traffic", json=route_data)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                results['without_traffic'] = data['route']
    except Exception as e:
        print(f"Error without traffic: {e}")
    
    # Test with live traffic
    print("🔄 Calculating with live traffic...")
    route_data["use_live_data"] = True
    try:
        response = requests.post(f"{BASE_URL}/route_with_live_traffic", json=route_data)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                results['with_traffic'] = data['route']
                results['traffic_analysis'] = data['live_traffic_analysis']
    except Exception as e:
        print(f"Error with traffic: {e}")
    
    # Compare results
    if 'without_traffic' in results and 'with_traffic' in results:
        without = results['without_traffic']
        with_traffic = results['with_traffic']
        
        print("\n📈 Comparison Results:")
        print(f"   Without traffic: {without['duration']} ({without['duration_seconds']}s)")
        print(f"   With traffic:    {with_traffic['duration']} ({with_traffic['duration_seconds']}s)")
        print(f"   Traffic delay:   {with_traffic['traffic_delay_seconds']}s ({with_traffic['delay_percentage']}%)")
        
        if results['traffic_analysis']['data_available']:
            print(f"   Live data from:  {', '.join(results['traffic_analysis']['sources_used'])}")
        else:
            print(f"   Using pattern-based estimation")

def main():
    """Main test function"""
    print("🚀 Live Traffic Integration Test")
    print("=" * 50)
    
    # Test API status
    test_live_traffic_status()
    
    # Test route with live traffic
    test_route_with_live_traffic()
    
    # Test comparison
    test_comparison_with_without_traffic()
    
    print("\n" + "=" * 50)
    print("📋 Setup Instructions:")
    print("1. Copy .env.example to .env")
    print("2. Add your API keys to .env:")
    print("   - HERE_API_KEY (free tier available)")
    print("   - MAPBOX_ACCESS_TOKEN (good free tier)")
    print("   - TOMTOM_API_KEY (free tier available)")
    print("3. Restart your Flask application")
    print("4. Run this test again to see live data in action!")

if __name__ == "__main__":
    main()
