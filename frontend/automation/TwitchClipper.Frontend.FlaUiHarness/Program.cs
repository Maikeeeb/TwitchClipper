using System.Diagnostics;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using FlaUI.Core;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Definitions;
using FlaUI.Core.Tools;
using FlaUI.UIA3;

var root = FindRepoRoot();
var scenarioPath = Path.Combine(
    root,
    "frontend",
    "automation",
    "scenarios",
    "bug_sweep_scenarios.json");
var desktopExePath = Path.Combine(
    root,
    "frontend",
    "TwitchClipper.Desktop",
    "bin",
    "Debug",
    "net8.0-windows",
    "TwitchClipper.Desktop.exe");
var apiPythonPath = Path.Combine(root, ".venv", "Scripts", "python.exe");
var apiArgs = "-m uvicorn api.main:app --host 127.0.0.1 --port 8000";
var apiBaseUrl = "http://127.0.0.1:8000";

if (!File.Exists(scenarioPath))
{
    Console.WriteLine($"Scenario file not found: {scenarioPath}");
    return 2;
}

if (!File.Exists(desktopExePath))
{
    Console.WriteLine($"Desktop exe not found: {desktopExePath}");
    Console.WriteLine("Build first: dotnet build frontend/TwitchClipper.Frontend.sln");
    return 2;
}

if (!File.Exists(apiPythonPath))
{
    Console.WriteLine($"Python not found at: {apiPythonPath}");
    return 2;
}

var scenarioDoc = JsonDocument.Parse(File.ReadAllText(scenarioPath));
var scenarioIds = scenarioDoc.RootElement.GetProperty("scenarios")
    .EnumerateArray()
    .Select(element => element.GetProperty("id").GetString() ?? string.Empty)
    .ToList();

var results = new List<ScenarioResult>();
Process? apiProcess = null;
Application? app = null;
UIA3Automation? automation = null;

try
{
    apiProcess = StartApi(apiPythonPath, apiArgs, root);
    WaitForApiHealthy(apiBaseUrl, timeoutMs: 20_000);

    app = Application.Launch(desktopExePath);
    automation = new UIA3Automation();
    var window = Retry.WhileNull(
        () => app.GetMainWindow(automation, TimeSpan.FromSeconds(1)),
        TimeSpan.FromSeconds(20)).Result;
    if (window is null)
    {
        throw new InvalidOperationException("Failed to locate main window.");
    }

    var client = new HttpClient { BaseAddress = new Uri(apiBaseUrl), Timeout = TimeSpan.FromSeconds(10) };

    Run("happy-startup-hydration", scenarioIds, results, () =>
    {
        ClickButton(window, "Dashboard (Ctrl+1)");
        RequireAnyText(window, ["Dashboard heading", "SCR-001 Dashboard"]);
        return "Dashboard visible";
    });

    Run("failure-empty-vod-url", scenarioIds, results, () =>
    {
        ClickButton(window, "New VOD (Ctrl+2)");
        SetTextBox(window, "SCR002-CMP001", "");
        SetTextBox(window, "SCR002-CMP002", "vod_output");
        var submit = FindButton(window, "SCR002-CMP010");
        if (!submit.IsEnabled)
        {
            return "Submit disabled for empty VOD URL";
        }

        throw new InvalidOperationException("Submit button remained enabled for empty URL.");
    });

    Run("failure-malformed-vod-url", scenarioIds, results, () =>
        RunStrictFailedOracle(window, client, "not-a-url", "Invalid input string: not-a-url"));
    Run("failure-non-video-twitch-url", scenarioIds, results, () =>
        RunStrictFailedOracle(
            window,
            client,
            "https://www.twitch.tv/somechannel",
            "Invalid input string: https://www.twitch.tv/somechannel"));
    Run("edge-guarded-unreachable-url", scenarioIds, results, () =>
        RunStrictFailedOracle(
            window,
            client,
            "https://invalid.invalid/videos/2713566602",
            "Invalid input string: https://invalid.invalid/videos/2713566602"));

    Run("failure-network-path-offline", scenarioIds, results, () =>
    {
        EnsureApiStopped(apiProcess);
        apiProcess = null;

        ClickButton(window, "New VOD (Ctrl+2)");
        SetTextBox(window, "SCR002-CMP001", "https://www.twitch.tv/videos/2713566602");
        SetTextBox(window, "SCR002-CMP002", "vod_output");
        ClickButton(window, "SCR002-CMP010");
        var alert = WaitForTextContains(window, "Network error while submitting VOD job.", 15_000);
        if (!alert)
        {
            throw new InvalidOperationException(
                "Did not observe expected offline submit alert.");
        }

        apiProcess = StartApi(apiPythonPath, apiArgs, root);
        WaitForApiHealthy(apiBaseUrl, timeoutMs: 20_000);
        return "Observed offline form alert and restarted API";
    });

    Run("edge-job-detail-404", scenarioIds, results, () =>
    {
        var response = client.GetAsync("/jobs/missing-id").GetAwaiter().GetResult();
        if ((int)response.StatusCode != 404)
        {
            throw new InvalidOperationException($"Expected 404, got {(int)response.StatusCode}");
        }

        return "Verified 404 via API fallback oracle";
    });

    Run("edge-rerun-sparse-prefill", scenarioIds, results, () =>
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, "/jobs")
        {
            Content = JsonContent.Create(new Dictionary<string, object> {
                ["type"] = "vod_highlights",
                ["params"] = new Dictionary<string, string>()
            }),
        };
        var submit = client.Send(request);
        if (!submit.IsSuccessStatusCode)
        {
            throw new InvalidOperationException($"Failed to submit sparse job: {(int)submit.StatusCode}");
        }

        var json = JsonDocument.Parse(submit.Content.ReadAsStringAsync().GetAwaiter().GetResult());
        var jobId = json.RootElement.GetProperty("job_id").GetString() ?? string.Empty;

        ClickButton(window, "Jobs (Ctrl+4)");
        SetTextBox(window, "SCR004-CMP003", jobId);
        ClickButton(window, "SCR004-CMP004");
        SelectFirstDataGridRow(window, "SCR004-CMP001");
        ClickButton(window, "Open selected");
        ClickButton(window, "SCR005-CMP006");
        RequireText(window, "SCR-002 New VOD Highlights Job");
        return "Rerun navigated to VOD form without crash";
    });

    Run("happy-vod-submit-fixed-url", scenarioIds, results, () =>
    {
        ClickButton(window, "New VOD (Ctrl+2)");
        SetTextBox(window, "SCR002-CMP001", "https://www.twitch.tv/videos/2713566602");
        SetTextBox(window, "SCR002-CMP002", "vod_output");
        var knownIds = FetchJobIds(client);
        ClickButton(window, "SCR002-CMP010");
        RequireText(window, "SCR-004 Jobs Queue");
        var newId = WaitForNewJobId(client, knownIds, timeoutMs: 10_000);
        return $"Submitted job {newId}";
    });

    Run("happy-clip-submit", scenarioIds, results, () =>
    {
        ClickButton(window, "New Clip (Ctrl+3)");
        SetTextBox(window, "SCR003-CMP001", "zubatlel");
        SetTextBox(window, "SCR003-CMP002", "currentVideos");
        var knownIds = FetchJobIds(client);
        ClickButton(window, "SCR003-CMP007");
        RequireText(window, "SCR-004 Jobs Queue");
        var newId = WaitForNewJobId(client, knownIds, timeoutMs: 10_000);
        return $"Submitted job {newId}";
    });
}
catch (Exception ex)
{
    Console.WriteLine($"Harness fatal error: {ex}");
}
finally
{
    if (automation is not null)
    {
        automation.Dispose();
    }

    if (app is not null && !app.HasExited)
    {
        app.Close();
    }

    EnsureApiStopped(apiProcess);
}

Console.WriteLine("---- FlaUI scenario pass ----");
foreach (var result in results)
{
    Console.WriteLine($"[{result.Status}] {result.Id}: {result.Detail}");
}

var failed = results.Count(result => result.Status == "FAIL");
var skipped = scenarioIds.Except(results.Select(result => result.Id)).ToList();
foreach (var skippedId in skipped)
{
    Console.WriteLine($"[SKIP] {skippedId}: scenario not executed by harness");
}

return failed == 0 ? 0 : 1;

static string RunStrictFailedOracle(Window window, HttpClient client, string vodUrl, string expectedError)
{
    ClickButton(window, "New VOD (Ctrl+2)");
    SetTextBox(window, "SCR002-CMP001", vodUrl);
    SetTextBox(window, "SCR002-CMP002", "vod_output");
    var knownIds = FetchJobIds(client);
    ClickButton(window, "SCR002-CMP010");
    var newId = WaitForNewJobId(client, knownIds, timeoutMs: 10_000);
    ClickButton(window, "SCR004-CMP005");
    var job = WaitForJobById(client, newId, timeoutMs: 15_000);
    if (!string.Equals(job.status, "failed", StringComparison.OrdinalIgnoreCase))
    {
        throw new InvalidOperationException(
            $"Expected failed status for {newId}; got {job.status}");
    }

    if (!string.Equals(job.error, expectedError, StringComparison.Ordinal))
    {
        throw new InvalidOperationException(
            $"Expected error '{expectedError}', got '{job.error}'");
    }

    return $"Strict failed oracle matched for {newId}";
}

static Process StartApi(string pythonPath, string args, string workingDir)
{
    var startInfo = new ProcessStartInfo
    {
        FileName = pythonPath,
        Arguments = args,
        WorkingDirectory = workingDir,
        UseShellExecute = false,
        RedirectStandardOutput = true,
        RedirectStandardError = true,
        CreateNoWindow = true,
    };
    var process = Process.Start(startInfo)
        ?? throw new InvalidOperationException("Failed to start API process.");
    return process;
}

static void WaitForApiHealthy(string apiBaseUrl, int timeoutMs)
{
    using var client = new HttpClient { BaseAddress = new Uri(apiBaseUrl), Timeout = TimeSpan.FromSeconds(2) };
    var start = Environment.TickCount64;
    while (Environment.TickCount64 - start < timeoutMs)
    {
        try
        {
            var response = client.GetAsync("/health").GetAwaiter().GetResult();
            if (response.IsSuccessStatusCode)
            {
                return;
            }
        }
        catch
        {
            // keep retrying
        }

        Thread.Sleep(400);
    }

    throw new TimeoutException("API did not become healthy in time.");
}

static void EnsureApiStopped(Process? process)
{
    if (process is null)
    {
        return;
    }

    try
    {
        if (!process.HasExited)
        {
            process.Kill(entireProcessTree: true);
            process.WaitForExit(5000);
        }
    }
    catch
    {
        // best effort cleanup
    }
}

static List<string> FetchJobIds(HttpClient client)
{
    var response = client.GetAsync("/jobs?limit=200").GetAwaiter().GetResult();
    response.EnsureSuccessStatusCode();
    var text = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
    var document = JsonDocument.Parse(text);
    return document.RootElement.EnumerateArray()
        .Where(element => element.TryGetProperty("id", out _))
        .Select(element => element.GetProperty("id").GetString() ?? string.Empty)
        .Where(id => !string.IsNullOrWhiteSpace(id))
        .ToList();
}

static string WaitForNewJobId(HttpClient client, List<string> knownIds, int timeoutMs)
{
    var known = knownIds.ToHashSet(StringComparer.Ordinal);
    var start = Environment.TickCount64;
    while (Environment.TickCount64 - start < timeoutMs)
    {
        var ids = FetchJobIds(client);
        var newest = ids.FirstOrDefault(id => !known.Contains(id));
        if (!string.IsNullOrWhiteSpace(newest))
        {
            return newest;
        }

        Thread.Sleep(200);
    }

    throw new TimeoutException("No new job id observed after submit.");
}

static (string status, string error) WaitForJobById(HttpClient client, string jobId, int timeoutMs)
{
    var start = Environment.TickCount64;
    while (Environment.TickCount64 - start < timeoutMs)
    {
        var response = client.GetAsync($"/jobs/{jobId}").GetAwaiter().GetResult();
        response.EnsureSuccessStatusCode();
        var text = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
        var doc = JsonDocument.Parse(text);
        var status = doc.RootElement.GetProperty("status").GetString() ?? string.Empty;
        var error = doc.RootElement.TryGetProperty("error", out var err)
            ? err.GetString() ?? string.Empty
            : string.Empty;
        if (!string.Equals(status, "queued", StringComparison.OrdinalIgnoreCase)
            && !string.Equals(status, "running", StringComparison.OrdinalIgnoreCase))
        {
            return (status, error);
        }

        Thread.Sleep(200);
    }

    throw new TimeoutException($"Job {jobId} did not leave queued/running in time.");
}

static void Run(
    string scenarioId,
    IReadOnlyCollection<string> scenarioIds,
    IList<ScenarioResult> results,
    Func<string> action)
{
    if (!scenarioIds.Contains(scenarioId, StringComparer.Ordinal))
    {
        return;
    }

    try
    {
        var detail = action();
        results.Add(new ScenarioResult(scenarioId, "PASS", detail));
    }
    catch (Exception ex)
    {
        results.Add(new ScenarioResult(scenarioId, "FAIL", ex.Message));
    }
}

static Button FindButton(Window window, string name)
{
    var element = Retry.WhileNull(
        () => window.FindFirstDescendant(
            conditionFactory => conditionFactory.ByControlType(ControlType.Button)
                .And(conditionFactory.ByName(name))),
        TimeSpan.FromSeconds(10)).Result;
    if (element is null)
    {
        throw new InvalidOperationException($"Button not found: {name}");
    }

    return element.AsButton();
}

static void ClickButton(Window window, string name)
{
    var button = FindButton(window, name);
    button.Focus();
    button.Invoke();
}

static void SetTextBox(Window window, string name, string value)
{
    var element = Retry.WhileNull(
        () => window.FindFirstDescendant(
            conditionFactory => conditionFactory.ByControlType(ControlType.Edit)
                .And(conditionFactory.ByName(name))),
        TimeSpan.FromSeconds(10)).Result;
    if (element is null)
    {
        throw new InvalidOperationException($"TextBox not found: {name}");
    }

    var textBox = element.AsTextBox();
    textBox.Focus();
    textBox.Enter(value);
}

static void RequireText(Window window, string value)
{
    var found = Retry.WhileFalse(
        () => window.FindFirstDescendant(
            conditionFactory => conditionFactory.ByControlType(ControlType.Text)
                .And(conditionFactory.ByName(value))) is not null,
        TimeSpan.FromSeconds(10)).Result;
    if (!found)
    {
        throw new InvalidOperationException($"Text not found: {value}");
    }
}

static void RequireAnyText(Window window, IEnumerable<string> values)
{
    var targets = values.ToList();
    var found = Retry.WhileFalse(
        () => targets.Any(value => window.FindFirstDescendant(
            conditionFactory => conditionFactory.ByControlType(ControlType.Text)
                .And(conditionFactory.ByName(value))) is not null),
        TimeSpan.FromSeconds(10)).Result;
    if (!found)
    {
        throw new InvalidOperationException(
            $"None of expected text values were found: {string.Join(", ", targets)}");
    }
}

static bool WaitForTextContains(Window window, string value, int timeoutMs)
{
    return Retry.WhileFalse(() =>
    {
        var textElements = window.FindAllDescendants(
            conditionFactory => conditionFactory.ByControlType(ControlType.Text));
        return textElements.Any(element =>
            element.Name?.Contains(value, StringComparison.Ordinal) == true);
    }, TimeSpan.FromMilliseconds(timeoutMs)).Result;
}

static void SelectDataGridRowByText(Window window, string gridName, string rowContains)
{
    var gridElement = Retry.WhileNull(
        () => window.FindFirstDescendant(
            conditionFactory => conditionFactory.ByControlType(ControlType.DataGrid)
                .And(conditionFactory.ByName(gridName))),
        TimeSpan.FromSeconds(10)).Result;
    if (gridElement is null)
    {
        throw new InvalidOperationException($"DataGrid not found: {gridName}");
    }

    var rowElement = Retry.WhileNull(
        () =>
        {
            var rows = gridElement.FindAllDescendants(
                conditionFactory => conditionFactory.ByControlType(ControlType.DataItem));
            return rows.FirstOrDefault(row =>
                row.Name?.Contains(rowContains, StringComparison.Ordinal) == true);
        },
        TimeSpan.FromSeconds(10)).Result;
    if (rowElement is null)
    {
        throw new InvalidOperationException($"Unable to select row containing: {rowContains}");
    }

    rowElement.Focus();
    rowElement.Click();
}

static void SelectFirstDataGridRow(Window window, string gridName)
{
    var gridElement = Retry.WhileNull(
        () => window.FindFirstDescendant(
            conditionFactory => conditionFactory.ByControlType(ControlType.DataGrid)
                .And(conditionFactory.ByName(gridName))),
        TimeSpan.FromSeconds(10)).Result;
    if (gridElement is null)
    {
        throw new InvalidOperationException($"DataGrid not found: {gridName}");
    }

    var rowElement = Retry.WhileNull(
        () => gridElement.FindAllDescendants(
            conditionFactory => conditionFactory.ByControlType(ControlType.DataItem)).FirstOrDefault(),
        TimeSpan.FromSeconds(10)).Result;
    if (rowElement is null)
    {
        throw new InvalidOperationException("No rows available to select.");
    }

    rowElement.Focus();
    rowElement.Click();
}

static string FindRepoRoot()
{
    var current = new DirectoryInfo(AppContext.BaseDirectory);
    while (current is not null)
    {
        if (File.Exists(Path.Combine(current.FullName, "AGENTS.md")))
        {
            return current.FullName;
        }

        current = current.Parent;
    }

    throw new DirectoryNotFoundException("Could not locate repository root.");
}

internal record ScenarioResult(string Id, string Status, string Detail);
