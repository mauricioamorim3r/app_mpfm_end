' start_server_hidden.vbs
' Inicia o servidor MPFM Manager em segundo plano (sem janela visível).
' Chamado pelo Agendador de Tarefas ao fazer login. Nao requer admin.

Dim fso, scriptDir, appDir, pidFile, logOut, objShell, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
appDir    = fso.GetParentFolderName(scriptDir)
pidFile   = appDir & "\.tmp_server_pid.txt"
logOut    = appDir & "\.tmp_server_out.log"

Set objShell = CreateObject("WScript.Shell")

' Verifica se já está rodando (porta 8765)
Dim bInUse
bInUse = False
On Error Resume Next
Dim oNet
Set oNet = CreateObject("WScript.Network")
Dim result
result = objShell.Run("cmd /c netstat -ano | findstr :8765 | findstr LISTENING > nul 2>&1", 0, True)
If result = 0 Then bInUse = True
On Error GoTo 0

If bInUse Then
    WScript.Quit 0
End If

' Inicia server.py sem janela (windowStyle = 0)
objShell.CurrentDirectory = appDir
cmd = "python server.py"
objShell.Run cmd, 0, False
