using System.Diagnostics;
using System.IO;

namespace TwitchClipper.Desktop.Services;

public interface IPathOpener
{
    bool TryOpenPath(string? path, out string errorMessage);
}

public sealed class PathOpener : IPathOpener
{
    public bool TryOpenPath(string? path, out string errorMessage)
    {
        errorMessage = string.Empty;
        if (string.IsNullOrWhiteSpace(path))
        {
            errorMessage = "No output path is available for this job.";
            return false;
        }

        if (!File.Exists(path) && !Directory.Exists(path))
        {
            errorMessage = "The output path does not exist or cannot be accessed.";
            return false;
        }

        Process.Start(new ProcessStartInfo
        {
            FileName = path,
            UseShellExecute = true,
        });
        return true;
    }
}
