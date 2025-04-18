const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { execFile } = require('child_process');

// Configure for packaging
const isPackaged = process.argv.includes('--packaged');
const flaskPath = isPackaged
  ? path.join(process.resourcesPath, 'app.exe')
  : path.join(__dirname, '..', 'app.py');

let mainWindow;
let flaskProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      webSecurity: false // Disable only for development
    },
    icon: path.join(__dirname, '..', 'assets', 'icon.png')
  });

  // Load Flask server
  const startFlask = () => {
    if (isPackaged) {
      flaskProcess = execFile(flaskPath, {
        cwd: process.resourcesPath
      });
    } else {
      flaskProcess = require('child_process').spawn('python', [flaskPath]);
    }

    flaskProcess.stdout.on('data', (data) => {
      console.log(`Flask: ${data}`);
    });

    flaskProcess.stderr.on('data', (data) => {
      console.error(`Flask error: ${data}`);
    });

    flaskProcess.on('close', (code) => {
      if (code !== 0) console.error(`Flask exited with code ${code}`);
    });
  };

  // Start Flask and load page
  startFlask();
  mainWindow.loadURL('http://localhost:5000', {
    extraHeaders: 'Content-Security-Policy: default-src \'self\' \'unsafe-inline\''
  });

  // Development tools
  if (!isPackaged) {
    mainWindow.webContents.openDevTools();
  }
}

// App lifecycle
app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (flaskProcess) flaskProcess.kill();
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

// Cleanup on exit
process.on('SIGTERM', () => {
  if (flaskProcess) flaskProcess.kill();
  app.quit();
});