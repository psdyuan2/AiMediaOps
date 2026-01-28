const { app, BrowserWindow, ipcMain, protocol } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const { watch } = require('fs');
const net = require('net');

// 注册自定义协议以支持加载本地资源（用于 ES 模块）
function registerLocalResourceProtocol() {
  protocol.registerFileProtocol('app', (request, callback) => {
    const url = request.url.substr(6); // 移除 'app://' 前缀
    const filePath = path.normalize(path.join(__dirname, '..', url));
    callback({ path: filePath });
  }, (error) => {
    if (error) {
      console.error('Failed to register app protocol:', error);
    } else {
      console.log('✅ Registered app:// protocol');
    }
  });
}

let mainWindow = null;
let backendProcess = null;
let logWatchers = [];

// 应用数据目录
const APP_DATA_DIR = path.join(require('os').homedir(), '.moke');
const LOGS_DIR = path.join(APP_DATA_DIR, 'logs');
const BOOTSTRAP_LOG = path.join(LOGS_DIR, 'bootstrap.log');
const BACKEND_LOG = path.join(LOGS_DIR, 'backend.log');

// 确保日志目录存在
function ensureLogsDir() {
  if (!fs.existsSync(LOGS_DIR)) {
    fs.mkdirSync(LOGS_DIR, { recursive: true });
  }
}

// 检查后端服务是否运行
function checkBackendHealth(port = 8765) {
  return new Promise((resolve) => {
    const socket = net.createConnection(port, '127.0.0.1', () => {
      socket.end();
      resolve(true);
    });
    socket.on('error', () => resolve(false));
    socket.setTimeout(1000, () => {
      socket.destroy();
      resolve(false);
    });
  });
}

// 读取日志文件的最后 N 行
function readLogTail(filePath, lines = 100) {
  try {
    if (!fs.existsSync(filePath)) {
      return '';
    }
    const content = fs.readFileSync(filePath, 'utf-8');
    const allLines = content.split('\n');
    return allLines.slice(-lines).join('\n');
  } catch (error) {
    return `Error reading log: ${error.message}\n`;
  }
}

// 监听日志文件变化并发送给前端
function watchLogFile(filePath, eventName) {
  if (!fs.existsSync(filePath)) {
    // 文件不存在时，创建一个空文件
    fs.writeFileSync(filePath, '', 'utf-8');
  }

  let lastSize = 0;
  try {
    lastSize = fs.statSync(filePath).size;
  } catch (error) {
    console.error(`Error getting file size for ${filePath}:`, error);
  }

  // 先发送现有内容
  const existingContent = readLogTail(filePath, 200);
  if (existingContent && mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send(eventName, existingContent);
  }

  // 监听文件变化
  const watcher = fs.watchFile(filePath, { interval: 300 }, (curr, prev) => {
    if (!mainWindow || mainWindow.isDestroyed()) {
      return;
    }

    if (curr.size > prev.size) {
      try {
        const stream = fs.createReadStream(filePath, {
          start: prev.size,
          end: curr.size,
          encoding: 'utf-8'
        });
        
        let newContent = '';
        stream.on('data', (chunk) => {
          newContent += chunk;
        });
        
        stream.on('end', () => {
          if (newContent && mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send(eventName, newContent);
          }
        });

        stream.on('error', (error) => {
          console.error(`Error reading log file ${filePath}:`, error);
        });
      } catch (error) {
        console.error(`Error creating read stream for ${filePath}:`, error);
      }
    }
  });

  logWatchers.push({ filePath });
  return watcher;
}

// 启动后端服务
async function startBackend() {
  const isDev = !app.isPackaged;
  const resourcesPath = isDev 
    ? path.join(__dirname, '..')
    : process.resourcesPath;
  
  const backendDir = path.join(resourcesPath, 'backend');
  
  // 平台检测
  const isWindows = process.platform === 'win32';
  const isMac = process.platform === 'darwin';
  
  // 根据平台选择可执行文件和脚本路径
  const binaryPath = isWindows 
    ? path.join(backendDir, 'moke-backend.exe')
    : path.join(backendDir, 'moke-backend');
  
  const binaryScriptPath = isWindows 
    ? path.join(backendDir, 'start_backend_binary.bat')
    : path.join(backendDir, 'start_backend_binary.sh');
  
  const pythonScriptPath = isWindows
    ? path.join(backendDir, 'start_backend.bat')
    : path.join(backendDir, 'start_backend.sh');
  
  let scriptPath;
  let useBinary = false;
  
  // 检查二进制文件是否存在
  if (fs.existsSync(binaryPath)) {
    scriptPath = binaryScriptPath;
    useBinary = true;
    console.log('✅ 使用 PyInstaller 打包的后端可执行文件');
  } else if (fs.existsSync(binaryScriptPath)) {
    scriptPath = binaryScriptPath;
    useBinary = true;
    console.log('✅ 使用二进制启动脚本');
  } else {
    scriptPath = pythonScriptPath;
    console.log('⚠️  使用 Python 脚本启动（回退模式）');
  }
  
  // 检查脚本是否存在
  if (!fs.existsSync(scriptPath)) {
    console.error('❌ 后端启动脚本不存在:', scriptPath);
    throw new Error(`Backend startup script not found: ${scriptPath}`);
  }
  // 设置环境变量
  const env = {
    ...process.env,
    APP_RESOURCES: resourcesPath,
    APP_DATA_DIR: APP_DATA_DIR,
    PYTHONPATH: backendDir,
    API_HOST: '127.0.0.1',
    API_PORT: '8765',
    API_LOG_LEVEL: 'info'
  };

  // 设置 PLAYWRIGHT_BROWSERS_PATH
  // 在打包后，playwright-browsers 位于 backend 目录内（因为 extraResources 配置了复制 backend）
  const playwrightBrowsersPath = path.join(backendDir, 'playwright-browsers');
  if (fs.existsSync(playwrightBrowsersPath)) {
    env.PLAYWRIGHT_BROWSERS_PATH = playwrightBrowsersPath;
    console.log('✅ Found Playwright browsers at:', playwrightBrowsersPath);
  } else {
    // 尝试在 resources 根目录查找（旧逻辑，兼容）
    const altPath = path.join(resourcesPath, 'playwright-browsers');
    if (fs.existsSync(altPath)) {
      env.PLAYWRIGHT_BROWSERS_PATH = altPath;
      console.log('✅ Found Playwright browsers at (root):', altPath);
    } else {
      console.warn('⚠️  Playwright browsers not found');
    }
  }

  // 启动后端进程（根据平台选择不同的启动方式）
  console.log(`Starting backend with script: ${scriptPath}`);
  if (isWindows) {
    // Windows 使用 cmd.exe 或直接执行 .bat 文件
    backendProcess = spawn(scriptPath, [], {
      cwd: backendDir,
      env: env,
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: true  // Windows 需要 shell: true 来执行 .bat 文件
    });
  } else {
    // macOS/Linux 使用 bash
    backendProcess = spawn('bash', [scriptPath], {
      cwd: backendDir,
      env: env,
      stdio: ['ignore', 'pipe', 'pipe']
    });
  }

  // 将输出写入日志文件
  const logStream = fs.createWriteStream(BACKEND_LOG, { flags: 'a' });
  backendProcess.stdout.pipe(logStream);
  backendProcess.stderr.pipe(logStream);

  backendProcess.on('error', (error) => {
    console.error('Backend process error:', error);
    if (mainWindow) {
      mainWindow.webContents.send('backend-status', 'error');
    }
  });

  backendProcess.on('exit', (code) => {
    console.log(`Backend process exited with code ${code}`);
    if (mainWindow) {
      mainWindow.webContents.send('backend-status', 'stopped');
    }
  });

  return backendProcess;
}

// 等待后端服务就绪
async function waitForBackend(maxAttempts = 30) {
  for (let i = 0; i < maxAttempts; i++) {
    const isReady = await checkBackendHealth(8765);
    if (isReady) {
      return true;
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  return false;
}

function createWindow() {
  ensureLogsDir();

  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
      webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false // 临时禁用 webSecurity 以允许 ES 模块加载
    },
    show: false, // 先不显示，等后端就绪后再显示
    title: 'MoKe'
  });

  // 打开开发者工具以便调试
  mainWindow.webContents.openDevTools();

  // 加载前端应用
  const isDev = !app.isPackaged;
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    // 在打包环境中，前端文件在 extraResources 中
    // 路径应该是 resources/frontend/dist/index.html
    const resourcesPath = process.resourcesPath || path.join(__dirname, '..');
    const indexPath = path.join(resourcesPath, 'frontend', 'dist', 'index.html');
    
    console.log('=== Frontend Loading Debug ===');
    console.log('__dirname:', __dirname);
    console.log('process.resourcesPath:', process.resourcesPath);
    console.log('resourcesPath:', resourcesPath);
    console.log('indexPath:', indexPath);
    console.log('File exists:', fs.existsSync(indexPath));
    
    // 检查目录结构
    if (fs.existsSync(resourcesPath)) {
      console.log('Resources directory contents:', fs.readdirSync(resourcesPath));
    }
    if (fs.existsSync(path.join(resourcesPath, 'frontend'))) {
      console.log('Frontend directory contents:', fs.readdirSync(path.join(resourcesPath, 'frontend')));
    }
    if (fs.existsSync(path.join(resourcesPath, 'frontend', 'dist'))) {
      console.log('Dist directory contents:', fs.readdirSync(path.join(resourcesPath, 'frontend', 'dist')));
    }
    
    // 监听页面加载事件
    mainWindow.webContents.on('did-finish-load', () => {
      console.log('✅ Page loaded successfully');
    });
    
    mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL, isMainFrame) => {
      console.error('❌ Failed to load page:', {
        errorCode,
        errorDescription,
        validatedURL,
        isMainFrame
      });
    });
    
    mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
      console.log(`[Renderer ${level}] ${message} (${sourceId}:${line})`);
    });
    
    // 监听资源加载失败
    mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL, isMainFrame, frameProcessId, frameRoutingId) => {
      if (isMainFrame) {
        console.error('❌ Main frame failed to load:', {
          errorCode,
          errorDescription,
          validatedURL
        });
      } else {
        console.error('❌ Resource failed to load:', {
          errorCode,
          errorDescription,
          validatedURL
        });
      }
    });
    
    // 监听 DOM 就绪
    mainWindow.webContents.on('dom-ready', () => {
      console.log('✅ DOM ready');
      // 等待一下让脚本加载
      setTimeout(() => {
        // 检查 root 元素是否有内容
        mainWindow.webContents.executeJavaScript(`
          (function() {
            console.log('=== Frontend Debug Info ===');
            console.log('Root element:', document.getElementById('root'));
            console.log('Root innerHTML:', document.getElementById('root')?.innerHTML);
            console.log('Root children:', document.getElementById('root')?.children.length);
            console.log('Scripts:', Array.from(document.scripts).map(s => ({src: s.src, type: s.type, loaded: s.readyState})));
            console.log('Stylesheets:', Array.from(document.styleSheets).map(s => s.href));
            
            // 检查是否有错误
            const scripts = Array.from(document.scripts);
            scripts.forEach((script, index) => {
              script.onerror = (e) => {
                console.error('Script load error:', script.src, e);
              };
              script.onload = () => {
                console.log('Script loaded:', script.src);
              };
            });
            
            // 检查 window.React 是否存在
            console.log('window.React:', typeof window.React);
            console.log('window.ReactDOM:', typeof window.ReactDOM);
          })();
        `).catch(err => console.error('Failed to execute debug script:', err));
      }, 2000);
    });
    
    // 尝试加载文件
    if (fs.existsSync(indexPath)) {
      // 使用 loadFile 加载，它会自动处理相对路径的资源
      // 注意：loadFile 会自动将相对路径转换为正确的 file:// URL
      const distDir = path.dirname(indexPath);
      console.log('Dist directory:', distDir);
      console.log('Assets directory exists:', fs.existsSync(path.join(distDir, 'assets')));
      
      mainWindow.loadFile(indexPath).then(() => {
        console.log('✅ loadFile succeeded, file path:', indexPath);
        // 等待页面加载后检查资源
        setTimeout(() => {
          mainWindow.webContents.executeJavaScript(`
            console.log('=== Resource Check ===');
            console.log('Current URL:', window.location.href);
            console.log('Checking loaded resources...');
            const scripts = Array.from(document.scripts);
            scripts.forEach((s, i) => {
              console.log(\`Script \${i}:\`, {
                src: s.src,
                readyState: s.readyState,
                async: s.async,
                defer: s.defer,
                type: s.type
              });
              if (s.readyState === 'loading' || s.readyState === 'uninitialized') {
                console.warn('⚠️ Script not loaded:', s.src);
                // 尝试手动加载
                s.onerror = (e) => {
                  console.error('❌ Script error:', s.src, e);
                };
              }
            });
            
            // 检查是否有 React 相关的全局变量
            setTimeout(() => {
              console.log('React check:', {
                React: typeof window.React,
                ReactDOM: typeof window.ReactDOM,
                rootContent: document.getElementById('root')?.innerHTML
              });
            }, 2000);
          `).catch(err => console.error('Failed to check resources:', err));
        }, 1000);
      }).catch((error) => {
        console.error('❌ Failed to load index.html:', error);
        // 如果 loadFile 失败，尝试使用 file:// URL
        const fileUrl = `file://${indexPath}`;
        console.log('Trying file:// URL:', fileUrl);
        mainWindow.loadURL(fileUrl).catch((urlError) => {
          console.error('❌ Failed to load with file:// URL:', urlError);
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.executeJavaScript(`
              document.body.innerHTML = '<div style="padding: 20px; font-family: system-ui;"><h1>加载失败</h1><p>无法加载应用资源。</p><p>错误: ${error.message}</p><p>路径: ${indexPath}</p></div>';
            `).catch(err => console.error('Failed to show error message:', err));
          }
        });
      });
    } else {
      console.error('❌ index.html not found at:', indexPath);
      // 尝试备用路径
      const altPath = path.join(__dirname, '../frontend/dist/index.html');
      console.log('Trying alternative path:', altPath);
      if (fs.existsSync(altPath)) {
        mainWindow.loadFile(altPath).catch((error) => {
          console.error('❌ Failed to load from alternative path:', error);
        });
      } else {
        console.error('❌ Alternative path also not found');
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.executeJavaScript(`
            document.body.innerHTML = '<div style="padding: 20px; font-family: system-ui;"><h1>文件未找到</h1><p>无法找到前端文件。</p><p>主路径: ${indexPath}</p><p>备用路径: ${altPath}</p></div>';
          `).catch(err => console.error('Failed to show error message:', err));
        }
      }
    }
  }

  // 启动日志监听
  watchLogFile(BOOTSTRAP_LOG, 'backend-bootstrap-log');
  watchLogFile(BACKEND_LOG, 'backend-log');

  // 启动后端服务
  mainWindow.webContents.once('did-finish-load', async () => {
    // 发送初始状态
    mainWindow.webContents.send('backend-status', 'starting');

    try {
      // 启动后端
      await startBackend();
      
      // 等待后端就绪
      const isReady = await waitForBackend(30);
      
      if (isReady) {
        mainWindow.webContents.send('backend-status', 'ready');
        // 延迟一点显示窗口，让前端有时间渲染启动卡片
        setTimeout(() => {
          mainWindow.show();
        }, 500);
      } else {
        mainWindow.webContents.send('backend-status', 'timeout');
        mainWindow.show(); // 即使超时也显示窗口，让用户看到错误
      }
    } catch (error) {
      console.error('Failed to start backend:', error);
      mainWindow.webContents.send('backend-status', `error: ${error.message}`);
      mainWindow.show();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC 处理器
ipcMain.handle('check-backend-health', async () => {
  return await checkBackendHealth(8765);
});

ipcMain.handle('get-log-content', async (event, logType) => {
  const logFile = logType === 'bootstrap' ? BOOTSTRAP_LOG : BACKEND_LOG;
  return readLogTail(logFile, 500);
});

// 在应用准备就绪前注册协议
app.on('ready', () => {
  // 注册自定义协议（仅在打包环境中需要）
  if (app.isPackaged) {
    try {
      registerLocalResourceProtocol();
      console.log('✅ Custom protocol registered');
    } catch (error) {
      console.error('Failed to register protocol:', error);
    }
  }
});

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  // 清理日志监听器
  logWatchers.forEach(({ filePath }) => {
    try {
      fs.unwatchFile(filePath);
    } catch (error) {
      console.error(`Error unwatching file ${filePath}:`, error);
    }
  });
  logWatchers = [];

  // 停止后端进程
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }

  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  // 清理日志监听器
  logWatchers.forEach(({ filePath }) => {
    try {
      fs.unwatchFile(filePath);
    } catch (error) {
      console.error(`Error unwatching file ${filePath}:`, error);
    }
  });
  logWatchers = [];

  // 清理资源
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
});
