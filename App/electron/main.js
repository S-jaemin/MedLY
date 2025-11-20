const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const child_process = require('child_process');
const fs = require('fs');

let mainWindow = null;
let pyProc = null;
let backendStarted = false;
const ENABLE_FILE_LOG = false; // For deploy

// -------- Logging Utility --------
function writeLog(msg) {
  // 1) 개발 중에는 콘솔에만 찍게 하고 싶으면:
  console.log(msg);

  // 2) 바탕화면 파일 로그는 비활성화
  if (!ENABLE_FILE_LOG) return;

  try {
    const logPath = path.join(app.getPath("desktop"), "medly_boot_log.txt");
    const time = new Date().toLocaleTimeString();
    fs.appendFileSync(logPath, `[${time}] ${msg}\n`);
  } catch (e) {}
}

// -------- Backend 실행 --------
function createPyProc() {
  if (backendStarted) {
    writeLog("⚠ Backend already started. Skip.");
    return;
  }
  backendStarted = true;

  let cmd = "";
  let args = [];
  let cwdPath = "";

  try {
    if (app.isPackaged) {
      const backendFolder = path.join(process.resourcesPath, "backend_deploy");
      cmd = path.join(backendFolder, "backend.exe");
      cwdPath = backendFolder;

      if (!fs.existsSync(cmd)) {
        writeLog(`❌ backend.exe NOT FOUND: ${cmd}`);
        return;
      }
      writeLog(`🚀 Launching backend: ${cmd}`);
    } else {
      const backendSourceDir = path.join(__dirname, "../backend");
      cmd = "python";
      args = [path.join(backendSourceDir, "main.py")];
      cwdPath = backendSourceDir;

      writeLog(`🚀 Launching dev backend: python ${args.join(" ")}`);
    }

    pyProc = child_process.spawn(cmd, args, {
      cwd: cwdPath,
      stdio: "pipe",
      windowsHide: true,
      detached: false
    });

    pyProc.stdout.on("data", d => writeLog(`📤 stdout: ${d}`));
    pyProc.stderr.on("data", d => writeLog(`❗ stderr: ${d}`));
    pyProc.on("close", code => writeLog(`⚠ backend exit: ${code}`));

  } catch (err) {
    writeLog(`❌ Failed to launch backend: ${err}`);
  }
}

// -------- Window 생성 --------
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1700,
    height: 1000,
    title: "Medly",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.loadFile(path.join(__dirname, "loading.html"));
}

// -------- UI 전환 --------
ipcMain.handle("load-main-ui", () => {
  if (mainWindow) {
    mainWindow.loadFile(path.join(__dirname, "index.html"));
  }
});

// -------- 앱 시작 --------
app.once("ready", () => {
  createWindow();
  createPyProc();
});

// -------- 앱 종료 처리 (중복 kill 방지) --------
app.on("will-quit", () => {
  writeLog("🔻 will-quit triggered.");
  if (pyProc) {
    try { pyProc.kill(); } catch (_) {}
  }
  try {
    child_process.execSync('taskkill /IM backend.exe /F', { stdio: "ignore" });
    writeLog("🗑 backend.exe terminated.");
  } catch (_) {}
});

// window-all-closed에는 backend 종료 절대 금지
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});