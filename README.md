# 云手机管理 Windows EXE 窗体程序

这是一个最基础的云手机管理窗体程序，用 Python 自带的 Tkinter 写成。

界面效果：

- 白色软件背景
- 4x4 共 16 个云手机窗口
- 小窗口颜色为 `#4a576a`
- 每个小窗口下面显示一个灰色模拟器编号
- 编号长度一样，并且连续递增

## 在 Mac 上预览

```bash
cd /Users/mac/windows_exe_demo
python3 main.py
```

如果能看到窗口、输入名字、点击按钮，就说明程序逻辑正常。

## 在 Windows 上本地打包

进入项目目录后双击：

```text
build_windows.bat
```

打包完成后，exe 在：

```text
dist\CloudPhoneManager.exe
```

## 用 GitHub Actions 自动打包 Windows exe

1. 把这个项目上传到 GitHub。
2. 进入 GitHub 仓库的 `Actions` 页面。
3. 选择 `Build Windows EXE`。
4. 点击 `Run workflow`。
5. 等执行完成后，在页面底部下载 `CloudPhoneManager-windows-exe`。

## 修改窗口内容

主要改这个文件：

```text
main.py
```

可以改标题、按钮文字、窗口大小、点击后的提示内容。
