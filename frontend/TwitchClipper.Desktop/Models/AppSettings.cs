namespace TwitchClipper.Desktop.Models;

public sealed class AppSettings
{
    public string ApiBaseUrl { get; set; } = "http://127.0.0.1:8000";

    public bool DeveloperMode { get; set; } = true;

    public int PollingIntervalMs { get; set; } = 3000;

    public int OfflineRetryBaseSeconds { get; set; } = 5;

    public int OfflineRetryMaxSeconds { get; set; } = 30;
}
