# 云手机管理 Windows EXE 窗体程序

这是一个面向 Windows 打包的 Tkinter 桌面程序，主程序是 `main.py`，打包后输出 `dist\CloudPhoneManager.exe`。

## 功能

- 白色主窗口，固定 4x4 共 16 个云手机卡片
- 支持上传视频并同步播放到所有云手机卡片
- 支持上传音频、暂停/继续、拖动进度
- 支持批量选择素材、批量改名
- 点击云手机可打开独立放大窗口

## Windows 本地打包

在 Windows 电脑安装 Python 3.12 或 3.11 后，双击项目里的：

```text
build_windows.bat
```

打包完成后文件在：

```text
dist\CloudPhoneManager.exe
```

也可以在命令行执行：

```bat
python -m pip install -r requirements.txt
python -m PyInstaller --clean --noconfirm CloudPhoneManager.spec
```

## GitHub Actions 打包

把项目上传到 GitHub 后，可在 Actions 里手动运行 `Build Windows EXE`，完成后下载 artifact：

```text
CloudPhoneManager-windows-exe
```

## 说明

- `CloudPhoneManager.spec` 是 Windows EXE 打包配置，不包含其他平台应用包配置。
- `windows_app.manifest` 用于启用 Windows 常用控件、DPI 感知和普通用户权限启动。
- Windows EXE 需要在 Windows 环境打包生成。
