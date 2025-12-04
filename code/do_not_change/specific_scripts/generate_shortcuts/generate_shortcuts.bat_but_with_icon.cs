// compile with:
// "%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /target:winexe /win32icon:shortcut_generator.ico /out:generate_shortcuts.bat_but_with_icon.exe generate_shortcuts.bat_but_with_icon.exe.cs

using System;
using System.Diagnostics;
using System.IO;

class Program
{
    static void Main()
    {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;

        string batPath = Path.Combine(
            baseDir,
            @"generate_shortcuts.bat"
        );

        if (!File.Exists(batPath))
        {
            return;
        }

        string args = "/C \"\"" + batPath + "\"\"";

        var psi = new ProcessStartInfo("cmd.exe", args);
        psi.WorkingDirectory = baseDir;
        psi.UseShellExecute = false;

        Process.Start(psi);
    }
}

