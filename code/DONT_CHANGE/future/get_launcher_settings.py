
def send_windows_notification(notification_title: str, message: str, app_id: str) -> None:
    import subprocess

    powershell_script = r"""
$titleText = if ($args.Count -gt 0) { $args[0] } else { "Python script" }
$messageText = if ($args.Count -gt 1) { $args[1] } else { "" }
$appId = if ($args.Count -gt 2 -and $args[2]) { $args[2] } else { "PyAppTemplate" }
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime] | Out-Null
$titleXml = [System.Security.SecurityElement]::Escape($titleText)
$messageXml = [System.Security.SecurityElement]::Escape($messageText)
$xml = @"
<toast>
  <visual>
    <binding template="ToastGeneric">
      <text>$titleXml</text>
      <text>$messageXml</text>
    </binding>
  </visual>
  <audio silent="true"/>
</toast>
"@
$doc = [Windows.Data.Xml.Dom.XmlDocument]::new()
$doc.LoadXml($xml)
$toast = [Windows.UI.Notifications.ToastNotification]::new($doc)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
"""
    try:
        subprocess.Popen(  # noqa:S603
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                powershell_script,
                notification_title,
                message,
                app_id,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        pass
