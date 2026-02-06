; launcher.nsi
; --------------------------------------
Name "Batch Launcher"
OutFile "launcher.exe"

; 1. HIDE THE WINDOW
; This prevents the "Installing..." window from appearing.
SilentInstall silent

; Standard settings
RequestExecutionLevel user
!include "LogicLib.nsh"

Section "Main"
    Var /GLOBAL BatchPath
    Var /GLOBAL BatchArg
    Var /GLOBAL MySelf

    ; ------------------------------------------
    ; ARGUMENT PARSING
    ; ------------------------------------------
    ; Argument 1 = launcher.exe (We skip this)
    ; Argument 2 = Batch File Path
    ; Argument 3 = The Argument to pass

    ; Get Batch Path (Index 2)
    Push 2
    Call GetParameter
    Pop $BatchPath

    ; Get Argument (Index 3)
    Push 3
    Call GetParameter
    Pop $BatchArg

    ; ------------------------------------------
    ; SAFETY CHECKS
    ; ------------------------------------------
    
    ; 1. Check for Recursive Loop (Launcher launching itself)
    StrCpy $MySelf "$EXEPATH"
    ${If} "$BatchPath" == "$MySelf"
        MessageBox MB_OK|MB_ICONSTOP "CRITICAL ERROR: Recursive Loop Detected!$\r$\nThe launcher attempted to run itself.$\r$\nCheck your shortcut arguments."
        Abort
    ${EndIf}

    ; 2. Check if the Batch file actually exists
    IfFileExists "$BatchPath" Found NotFound

    NotFound:
        ; This is the only time a window will pop up (Error mode)
        MessageBox MB_OK|MB_ICONSTOP "Error: Target batch file not found at:$\r$\n$BatchPath"
        Abort

    Found:
        ; ------------------------------------------
        ; EXECUTION
        ; ------------------------------------------
        ; We use 'Exec' so the launcher closes immediately after starting the batch.
        ; We removed 'cmd /k' so the batch runs naturally (closes when done).
        
        Exec '"$BatchPath" "$BatchArg"'
        
        Quit
SectionEnd

; --------------------------------------
; Helper Function: GetParameter
; --------------------------------------
Function GetParameter
    Exch $0
    Push $1
    Push $2
    Push $3
    Push $4
    Push $5
    StrCpy $5 $CMDLINE
    StrCpy $1 0
    StrCpy $2 0
    StrCpy $3 ""
    StrCpy $4 0
    Loop:
        StrCpy $R0 $5 1 $1
        StrLen $R1 $5
        IntCmp $1 $R1 EndLoop
        IntOp $1 $1 + 1
        StrCmp $R0 '"' ToggleQuote
        StrCmp $R0 " " CheckSpace
        StrCpy $3 "$3$R0"
        Goto Loop
    ToggleQuote:
        IntOp $4 $4 !
        Goto Loop
    CheckSpace:
        IntCmp $4 1 AppendSpace
        StrCmp $3 "" Loop
        IntOp $2 $2 + 1
        IntCmp $2 $0 FoundArg ResetArg
    AppendSpace:
        StrCpy $3 "$3 "
        Goto Loop
    ResetArg:
        StrCpy $3 ""
        Goto Loop
    FoundArg:
        Goto Done
    EndLoop:
        StrCmp $3 "" Done
        IntOp $2 $2 + 1
        IntCmp $2 $0 FoundArg
    Done:
        StrCpy $0 $3
        Pop $5
        Pop $4
        Pop $3
        Pop $2
        Pop $1
        Exch $0
FunctionEnd