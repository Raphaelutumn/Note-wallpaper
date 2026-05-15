' 备忘录壁纸引擎 — 静默启动器
' 双击此文件即可在后台启动壁纸引擎（无控制台窗口）
Dim objShell, fso, scriptDir, pythonExe, wallpaperScript

Set objShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' VBS 文件所在目录
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
wallpaperScript = scriptDir & "\wallpaper_engine.py"

If Not fso.FileExists(wallpaperScript) Then
    MsgBox "找不到 wallpaper_engine.py，请将此文件放在项目目录中。" & vbCrLf & "目录: " & scriptDir, 48, "备忘录壁纸"
    WScript.Quit 1
End If

' 查找 pythonw.exe
pythonExe = ""
Dim candidates(4)
candidates(0) = objShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python311\pythonw.exe"
candidates(1) = objShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python312\pythonw.exe"
candidates(2) = objShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python313\pythonw.exe"
candidates(3) = "C:\Python311\pythonw.exe"
candidates(4) = "C:\Python312\pythonw.exe"

Dim p
For Each p In candidates
    If fso.FileExists(p) Then
        pythonExe = p
        Exit For
    End If
Next

If pythonExe = "" Then
    pythonExe = "pythonw.exe"
End If

' 静默启动（窗口模式 0 = 隐藏）
objShell.Run """" & pythonExe & """ """ & wallpaperScript & """", 0, False

Set objShell = Nothing
Set fso = Nothing
