# 🚗 Advanced Routing Application - Thesis Project

## 📋 Project Description

This application was developed as a **thesis project** with the theme **"Implementation of Dijkstra Algorithm for Optimal Route Finding"**.

The application evolved from a simple Dijkstra algorithm implementation to a **complete routing system** with advanced features that compete with commercial applications like Google Maps.

## 🎯 Thesis Objectives

- **Main Goal**: Implementation and analysis of Dijkstra algorithm
- **Extension**: Comparison with advanced algorithms (A*, Bidirectional Search)
- **Practical Application**: Development of real-world web application
- **Innovation**: Integration of live traffic data and real-time visualization

## 🚀 Features

### 🧠 Routing Algorithms
- **Dijkstra Algorithm**: Classic implementation for accurate results
- **A* Algorithm**: With heuristics (Manhattan, Euclidean, Adaptive)
- **Bidirectional Dijkstra**: For long distances (2x faster)
- **Intelligent Algorithm Selection**: Automatic selection of optimal algorithm

### 📊 Live Traffic Integration
- **Multi-Source APIs**: HERE, MapBox, TomTom, Google Maps
- **Real-time Traffic Data**: Live delays and traffic conditions
- **Traffic Light Estimation**: Traffic light estimation in urban areas
- **Rush Hour Detection**: Peak hours recognition

### 🎨 Advanced Visualization
- **Traffic-Colored Routes**: Colored routes based on traffic
- **Interactive Legend**: Color guide explanation
- **Real-time Updates**: Live ETA and condition updates
- **WebSocket Support**: Real-time communication

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/routing-app
cd routing-app
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup API Keys
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
# You can use any text editor
notepad .env  # Windows
nano .env     # Linux/Mac
```

### 4. Get Required API Keys

#### Required APIs:
- **OpenRouteService API**: https://openrouteservice.org/ (Free)
  - Used for basic routing and map data
  - Sign up and get your `ORS_API_KEY`

- **TomTom Traffic API**: https://developer.tomtom.com/ (Free tier available)
  - Used for live traffic data and enhanced routing
  - Sign up and get your `TOMTOM_API_KEY`

#### Optional (for additional traffic data):
- **HERE Traffic API**: https://developer.here.com/ (Free tier)
- **MapBox**: https://www.mapbox.com/ (Good free tier)

### 5. Run the Application
```bash
python app.py
```

### 6. Open in Browser
```
http://localhost:5000
```

## 📊 Performance Results

### Algorithm Comparison
- **A* vs Dijkstra**: 5-10x faster for long distances
- **Bidirectional**: 2x faster for very long routes
- **Intelligent Selection**: Optimal performance for each scenario

### Time Accuracy
- **Live Traffic**: Real traffic data
- **Traffic Lights**: Estimation of 2-3 lights/km in urban areas
- **Rush Hour**: Multipliers up to 2.5x during peak hours

## 🏗️ Architecture

```
├── app.py                     # Flask web server
├── routing/
│   ├── dijkstra.py           # Main Dijkstra implementation
│   ├── astar_dijkstra.py     # A* algorithm implementation
│   ├── route_manager.py      # Route coordination
│   ├── osm_handler.py        # OpenStreetMap data processing
│   ├── live_traffic_manager.py # Live traffic integration
│   └── realtime_manager.py   # WebSocket real-time features
├── static/
│   ├── script.js            # Frontend JavaScript
│   └── style.css            # Responsive CSS styling
└── templates/
    └── index.html           # Main web interface
```

## 🔒 Security Notes

- **Never commit API keys** to version control
- The `.env` file is automatically ignored by Git
- Use the `.env.example` template for setup
- API keys are loaded securely using environment variables

## 🛠️ Technologies

### Backend
- **Python 3.x** - Core development language
- **Flask** - Web framework
- **Flask-SocketIO** - Real-time communication
- **Requests** - API integration

### Frontend
- **HTML5/CSS3** - Modern web standards
- **JavaScript ES6+** - Interactive functionality
- **Leaflet.js** - Interactive maps
- **Bootstrap 5** - Responsive design

### APIs & Data
- **OpenStreetMap** - Road network data
- **HERE Traffic API** - Live traffic data
- **MapBox API** - Traffic and routing data
- **TomTom API** - Traffic flow information

## 🎓 Academic Contribution

This project contributes to the academic community with:

1. **Practical Implementation**: Complete code for routing algorithms
2. **Performance Analysis**: Comparative analysis of algorithms
3. **Real-world Application**: Application on real data
4. **Open Source**: Available for educational purposes

## 👨‍💻 Author

**Student Name**: [Your Name]  
**Department**: [Computer Science/Computer Engineering Department]  
**University**: [University Name]  
**Year**: 2024

### 📱 Contact
- **LinkedIn**: [linkedin.com/in/your-profile](https://linkedin.com/in/your-profile)
- **GitHub**: [github.com/your-username](https://github.com/your-username)
- **Email**: your.email@example.com

## 📄 License

This project is available under the MIT License for educational purposes.

## 🙏 Acknowledgments

- **Supervising Professor**: [Professor Name]
- **OpenStreetMap Community**: For road network data
- **Traffic API Providers**: HERE, MapBox, TomTom
- **Open Source Community**: For libraries and tools

---

*This application was developed as part of a thesis project and serves as an example of applying theoretical algorithm knowledge to real-world problems.*

## 🚀 GitHub Upload Instructions

### Ready to Upload to GitHub:
1. **Initialize Git repository:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Advanced Routing Application - Thesis Project"
   ```

2. **Create GitHub repository** and push:
   ```bash
   git remote add origin https://github.com/your-username/routing-app.git
   git branch -M main
   git push -u origin main
   ```

### What Gets Uploaded:
- ✅ **All source code** (app.py, routing/, static/, templates/)
- ✅ **Configuration templates** (.env.example, .gitignore)
- ✅ **Documentation** (README.md, requirements.txt)
- ❌ **Your API keys** (.env file is automatically excluded)

## 🚨 Important Security Notice

**NEVER commit your `.env` file to GitHub!** It contains sensitive API keys. The `.gitignore` file is configured to prevent this, but always double-check before pushing to GitHub.

### Required API Keys for Users:
- **ORS_API_KEY**: OpenRouteService API (Free at https://openrouteservice.org/)
- **TOMTOM_API_KEY**: TomTom Traffic API (Free tier at https://developer.tomtom.com/)

If you accidentally commit API keys:
1. Immediately revoke/regenerate the keys
2. Remove them from Git history
3. Update your `.env` file with new keys
