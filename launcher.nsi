; launcher.nsi
; --------------------------------------
Name "Batch Launcher (Safe)"
OutFile "launcher.exe"

; Show window for debugging
ShowInstDetails show
AutoCloseWindow false
RequestExecutionLevel user
!include "LogicLib.nsh"

Section "Main"
    Var /GLOBAL BatchPath
    Var /GLOBAL BatchArg
    Var /GLOBAL MySelf

    DetailPrint "Parsing arguments..."

    ; --- FIX IS HERE ---
    ; Index 1 is the Launcher.exe itself. 
    ; Index 2 is the Batch File.
    ; Index 3 is the Argument.

    ; Get The Batch Path (Index 2)
    Push 2
    Call GetParameter
    Pop $BatchPath

    ; Get The Argument (Index 3)
    Push 3
    Call GetParameter
    Pop $BatchArg

    DetailPrint "Target Batch: $BatchPath"
    DetailPrint "Target Arg:   $BatchArg"

    ; --- SAFETY CHECK ---
    ; Prevent the launcher from running itself recursively
    StrCpy $MySelf "$EXEPATH"
    ${If} "$BatchPath" == "$MySelf"
        MessageBox MB_ICONSTOP "CRITICAL ERROR: Recursive Loop Detected!$\r$\nThe launcher attempted to run itself.$\r$\nCheck your shortcut arguments."
        Abort
    ${EndIf}

    ; Check if file exists
    IfFileExists "$BatchPath" Found NotFound

    NotFound:
        MessageBox MB_ICONSTOP "Error: Batch file not found at:$\r$\n$BatchPath"
        Abort

    Found:
        DetailPrint "Executing..."
        ; Run cmd /k to keep window open for debugging
        ExecWait 'cmd.exe /k ""$BatchPath" "$BatchArg""'
        
        DetailPrint "Done."
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