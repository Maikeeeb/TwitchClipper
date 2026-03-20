using System.Collections.ObjectModel;
using System.Text.Json;
using System.Windows.Input;
using TwitchClipper.Desktop.Commands;
using TwitchClipper.Desktop.Models;
using TwitchClipper.Desktop.Services;

namespace TwitchClipper.Desktop.ViewModels;

public sealed class JobDetailViewModel : ViewModelBase
{
    private readonly IApiClient _apiClient;
    private readonly IPathOpener _pathOpener;

    private JobResponseDto? _job;
    private JobDetailTab _selectedTab = JobDetailTab.Summary;
    private string _errorMessage = string.Empty;

    public JobDetailViewModel(IApiClient apiClient, IPathOpener pathOpener)
    {
        _apiClient = apiClient;
        _pathOpener = pathOpener;

        OpenOutputPathCommand = new RelayCommand(_ => OpenOutputPath());
        RerunWithPrefillCommand = new RelayCommand(_ => RerunRequested?.Invoke(_job));
        BackToQueueCommand = new RelayCommand(_ => BackRequested?.Invoke());
    }

    public event Action<JobResponseDto?>? RerunRequested;

    public event Action? BackRequested;

    public ICommand OpenOutputPathCommand { get; }

    public ICommand RerunWithPrefillCommand { get; }

    public ICommand BackToQueueCommand { get; }

    public JobResponseDto? Job
    {
        get => _job;
        set => SetProperty(ref _job, value);
    }

    public JobDetailTab SelectedTab
    {
        get => _selectedTab;
        set => SetProperty(ref _selectedTab, value);
    }

    public string ErrorMessage
    {
        get => _errorMessage;
        set => SetProperty(ref _errorMessage, value);
    }

    public ObservableCollection<string> ResultRows { get; } = [];

    public ObservableCollection<string> OutputRows { get; } = [];

    public async Task LoadJobDetailAsync(string jobId)
    {
        try
        {
            Job = await _apiClient.GetJobAsync(jobId);
            ErrorMessage = ExtractJobError(Job);
            BuildDisplayRows();
            if (Job?.Status == "failed")
            {
                SelectedTab = JobDetailTab.Error;
            }
        }
        catch (ApiException ex)
        {
            ErrorMessage = ex.Message;
            if (ex.StatusCode == System.Net.HttpStatusCode.NotFound)
            {
                ErrorMessage = "Job not found. It may have been removed.";
            }
        }
    }

    public void OpenOutputPath()
    {
        if (Job is null)
        {
            ErrorMessage = "No job selected.";
            return;
        }

        var path = ResolveBestOutputPath(Job);

        if (!_pathOpener.TryOpenPath(path, out var errorMessage))
        {
            ErrorMessage = errorMessage;
            return;
        }

        ErrorMessage = string.Empty;
    }

    private void BuildDisplayRows()
    {
        ResultRows.Clear();
        OutputRows.Clear();

        if (Job?.Result is { ValueKind: JsonValueKind.Object } result)
        {
            foreach (var property in result.EnumerateObject())
            {
                ResultRows.Add($"{property.Name}: {property.Value}");
            }
        }
        else
        {
            ResultRows.Add("No result yet.");
        }

        var hasOutputs = false;
        if (Job?.Outputs is { ValueKind: JsonValueKind.Object } outputs)
        {
            foreach (var property in outputs.EnumerateObject())
            {
                OutputRows.Add($"{property.Name}: {property.Value}");
                hasOutputs = true;
            }
        }

        if (!hasOutputs && Job?.Result is { ValueKind: JsonValueKind.Object } fallbackResult)
        {
            foreach (var property in fallbackResult.EnumerateObject())
            {
                if (property.Name.Contains("path", StringComparison.OrdinalIgnoreCase)
                    || property.Name.Contains("dir", StringComparison.OrdinalIgnoreCase))
                {
                    OutputRows.Add($"{property.Name}: {property.Value}");
                    hasOutputs = true;
                }
            }
        }

        if (!hasOutputs)
        {
            OutputRows.Add("No output paths available.");
        }
    }

    private static string ExtractJobError(JobResponseDto? job)
    {
        if (!string.IsNullOrWhiteSpace(job?.Error))
        {
            return job.Error;
        }

        if (job?.Result is { ValueKind: JsonValueKind.Object } result
            && result.TryGetProperty("error", out var errorValue)
            && errorValue.ValueKind == JsonValueKind.String)
        {
            return errorValue.GetString() ?? string.Empty;
        }

        return string.Empty;
    }

    private static string? ResolveBestOutputPath(JobResponseDto job)
    {
        if (TryResolvePathFromElement(job.Outputs, out var path))
        {
            return path;
        }

        if (TryResolvePathFromElement(job.Result, out path))
        {
            return path;
        }

        return null;
    }

    private static bool TryResolvePathFromElement(JsonElement? element, out string? path)
    {
        path = null;
        if (element is null || element.Value.ValueKind != JsonValueKind.Object)
        {
            return false;
        }

        var payload = element.Value;
        var preferredKeys = new[]
        {
            "montage_path",
            "montage",
            "output_path",
            "path",
            "clips_dir",
            "vod_path",
            "chat_path",
            "metadata_path",
        };

        foreach (var key in preferredKeys)
        {
            if (payload.TryGetProperty(key, out var value) && value.ValueKind == JsonValueKind.String)
            {
                path = value.GetString();
                if (!string.IsNullOrWhiteSpace(path))
                {
                    return true;
                }
            }
        }

        if (payload.TryGetProperty("paths", out var pathsValue)
            && pathsValue.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in pathsValue.EnumerateArray())
            {
                if (item.ValueKind == JsonValueKind.String)
                {
                    path = item.GetString();
                    if (!string.IsNullOrWhiteSpace(path))
                    {
                        return true;
                    }
                }
            }
        }

        foreach (var property in payload.EnumerateObject())
        {
            if (!property.Name.Contains("path", StringComparison.OrdinalIgnoreCase)
                && !property.Name.Contains("dir", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            if (property.Value.ValueKind == JsonValueKind.String)
            {
                path = property.Value.GetString();
                if (!string.IsNullOrWhiteSpace(path))
                {
                    return true;
                }
            }
        }

        return false;
    }
}
