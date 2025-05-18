# BeatHaven 🎵
BeatHaven is an interactive web application for music cataloging and recommendation. It combines a stylish frontend with backend data processing to visualize and manage music metadata such as song name, album, artist, tempo, mood, and more.

---

## Overview

### Pages & Interfaces
- **index.html**: Landing page showcasing featured albums and an entry to the dashboard.
- **login.html**: User login page to access the music dashboard.
- **dashboard.html**: Interactive dashboard to browse and search songs. Links to detailed track views.
- **BeatHaven.html**: Dynamic song details page showing metadata like energy, valence, tempo, and more.


---

## Project Structure

```bash
.
├── app1.py                # Backend logic
├── index.html             # Landing page
├── login.html             # User authentication UI
├── dashboard.html         # Song browsing and management
├── BeatHaven.html         # Individual song information page
├── styles.css             # UI styling for all pages
├── scripts.js             # Frontend interactivity and animations
└── README.md              # You’re here!
```
### ⚙ Features
--> Responsive UI with a smooth, music-themed design.

-->  Login system to manage access to the dashboard.

-->  Music dashboard for browsing by artist, album, genre, etc.

-->  Detailed analytics per track (e.g., tempo, energy, valence, loudness).

-->  Click-through interface to fetch and display song metadata dynamically.

--> Integrated search and filter capabilities via JavaScript.

### Prerequisites

1. **Python 3.x**

2. **Flask** (or any backend framework you're using)

3. **Browser** (Chrome/Brave recommended)

---

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/BeatHaven.git
cd BeatHaven

# Install Python dependencies (if using Flask)
pip install flask


# Run the backend server 
python app1.py
```
Customization
Modify styles.css to tweak the UI theme.

Add new song data into the backend or connect to your existing music database.

Use scripts.js to add more interactivity, transitions, or real-time search filtering.
