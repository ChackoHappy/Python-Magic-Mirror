# Python-Magic-Mirror
A magic mirror built using PyQt6 as the GUI.

This multithreaded program can be run on any device that can run Python. Therefore, old laptops or Raspberry Pis can be used to create the mirror.

## Features
- Real-time Cryptocurrency Market Display
- Current Weather Display
- Todoist Task Syncing
- Voice Activated Features
- Admin panel
- YouTube Searching and Playing

### Real-time Cryptocurrency Market Display
- Powered by CoinGecko
- Updates every 5 seconds

### Current Weather Display
- Powered by OpenWeatherMAP
- Updates every hour

### Todoist Tasks Syncing
- Syncs every hour
- Displays the top 3 tasks

### Voice Activated Features
- Powered by Google Speech Recognition
- Uses voices recognition to control several aspects of the mirror

### Admin Panel
- Web server run in a separate thread that will receive and send data
- Run on port 8000

### YouTube Searching and Playing
- User can search for YouTube video with voice command or with admin panel
- User can then select from a list of the top 9 search results

## Voice Commands
- search for ______ on youtube
  - Example: search for raspberry pi on youtube
- select _____
  - Used to select from the list of the top 9 YouTube search results
  - Example: select one
- pause youtube
  - Pauses currently playing YouTube video
- unpause youtube
  - Unpauses currently paused YouTube video
- close youtube
  - Closes currently open YouTube video
- close youtube menu
  - Closes currently open YouTube menu
- what is your address
  - Displays the device's IP address
  - IP address can then be used to access the admin panel
