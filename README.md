![Mixamo Harvester](https://github.com/paulpierre/MixamoHarvester/blob/main/mixamo.png?raw=true)

# 🌾 MixamoHarvester

**MixamoHarvester** is a tool for downloading and managing ALL Mixamo animations in bulk. Project was inspired by the fantastic [Mixamo Anims Downloader by gnuton](https://github.com/gnuton/mixamo_anims_downloader).

## ✨ Features
- Automatically downloads all available Mixamo characters and animations.
- Exports animations in `.fbx` format.
- Monitors export progress and retries when necessary.
- Uses multi-threading for faster processing.
- Implements robust error handling and retry mechanisms.
- Saves progress state to resume interrupted downloads.
- Skips existing files to avoid redundant downloads.
- Organizes animations by character ID for easy management.

## ⚙️ How It Works
1. **Authentication**: Make sure you have a valid Mixamo Bearer token and save it in `mixamo_token.txt`.
2. **Character Fetching**: The tool fetches all available characters from Mixamo's API and stores them in `characters.json`.
3. **Animation Processing**: For each character, the tool processes all available animations:
   - It skips animation packs and only processes individual motions.
   - For each animation, it retrieves the product data and exports the animation.
4. **Export and Download**:
   - The tool initiates the export process for each animation.
   - It monitors the export progress until completion.
   - Once the export is ready, it downloads the animation as an `.fbx` file.
5. **Organization and State Management**:
   - Downloaded files are saved in the `animations` directory with a naming convention of `{animation_name}_{character_id}.fbx`.
   - The script maintains a state file (`state.json`) to track processed animations and resume interrupted downloads.
6. **Concurrency**: The tool uses multi-threading (with a default of 5 threads) to process animations concurrently, improving overall performance.
7. **Error Handling**: Robust error handling and retry mechanisms are implemented to handle potential API failures or network issues.

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/paulpierre/MixamoHarvester.git
cd MixamoHarvester
```

### 2. Install Dependencies
```bash

# Create a new virtual environment
python -m venv env

# Activate the virtual environment
# On Windows:
# env\Scripts\activate

# On macOS and Linux:
source env/bin/activate

pip install -r requirements.txt
```

### 3. Add Mixamo Bearer Token
Ensure you have a valid bearer token from Mixamo. To retrieve it:

1. **Log into Mixamo**: Open [Mixamo](https://www.mixamo.com) and log into your account.
2. **Open Developer Tools**:
   - On **Windows/Linux**: Press `Ctrl + Shift + I` or `F12`.
   - On **macOS**: Press `Cmd + Option + I`.
3. **Go to the Console Tab**: In the developer tools, click the "Console" tab.
4. **Run the JavaScript Code**:
   Paste the following JavaScript code into the console to retrieve the Bearer token from `localStorage`:

```javascript
(function() {
    const token = localStorage.getItem('access_token');
    if (token) {
        console.log("🔑 Your Bearer Token is: " + token);
    } else {
        console.log("Bearer Token not found. Make sure you are logged into Mixamo.");
    }
})();
```

5. **Copy the Token**: The Bearer token will be displayed in the console output. Copy this token and save it to a file named `mixamo_token.txt`.

### 4. Run the Script
Run the script to start downloading animations:
```bash
python mixamo_harvester.py
```

## 📝 To Do
- Hey, you tell me. Open an issue.

## 🎓 Credits
This project was inspired by [gnuton’s mixamo_anims_downloader](https://github.com/gnuton/mixamo_anims_downloader).

## 🛡️ License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
