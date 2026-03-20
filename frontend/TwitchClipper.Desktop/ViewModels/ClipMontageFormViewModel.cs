using System.Windows.Input;
using System.Net.Http;
using TwitchClipper.Desktop.Commands;
using TwitchClipper.Desktop.Models;
using TwitchClipper.Desktop.Services;

namespace TwitchClipper.Desktop.ViewModels;

public sealed class ClipMontageFormViewModel : FormViewModelBase
{
    private readonly IApiClient _apiClient;

    private string _streamerNamesText = string.Empty;
    private string _currentVideosDir = "currentVideos";
    private bool _applyOverlay;
    private int? _maxClips;
    private int? _scrapePoolSize;
    private int? _perStreamerK;
    private string _formAlert = string.Empty;

    public ClipMontageFormViewModel(IApiClient apiClient, IDialogService dialogService)
        : base(dialogService)
    {
        _apiClient = apiClient;

        SubmitCommand = new AsyncRelayCommand(_ => SubmitAsync(), _ => CanSubmit);
        CancelCommand = new RelayCommand(_ => CancelRequested?.Invoke());
    }

    public event Action<string>? Submitted;

    public event Action? CancelRequested;

    public ICommand SubmitCommand { get; }

    public ICommand CancelCommand { get; }

    public string StreamerNamesText
    {
        get => _streamerNamesText;
        set
        {
            if (SetProperty(ref _streamerNamesText, value))
            {
                MarkDirty();
                Validate();
            }
        }
    }

    public string CurrentVideosDir
    {
        get => _currentVideosDir;
        set
        {
            if (SetProperty(ref _currentVideosDir, value))
            {
                MarkDirty();
                Validate();
            }
        }
    }

    public bool ApplyOverlay
    {
        get => _applyOverlay;
        set
        {
            if (SetProperty(ref _applyOverlay, value))
            {
                MarkDirty();
                Validate();
            }
        }
    }

    public int? MaxClips
    {
        get => _maxClips;
        set
        {
            if (SetProperty(ref _maxClips, value))
            {
                MarkDirty();
                Validate();
            }
        }
    }

    public int? ScrapePoolSize
    {
        get => _scrapePoolSize;
        set
        {
            if (SetProperty(ref _scrapePoolSize, value))
            {
                MarkDirty();
                Validate();
            }
        }
    }

    public int? PerStreamerK
    {
        get => _perStreamerK;
        set
        {
            if (SetProperty(ref _perStreamerK, value))
            {
                MarkDirty();
                Validate();
            }
        }
    }

    public string FormAlert
    {
        get => _formAlert;
        set => SetProperty(ref _formAlert, value);
    }

    public bool CanSubmit => !HasValidationErrors && !IsSubmitting;

    public void Validate()
    {
        var errors = new List<string>();
        var parsedNames = ParseStreamerNames();
        if (parsedNames.Count == 0)
        {
            errors.Add("At least one streamer name is required.");
        }

        if (string.IsNullOrWhiteSpace(CurrentVideosDir))
        {
            errors.Add("Current videos directory is required.");
        }

        if (MaxClips is < 0)
        {
            errors.Add("Max clips must be >= 0 when provided.");
        }

        if (ScrapePoolSize is < 0)
        {
            errors.Add("Scrape pool size must be >= 0 when provided.");
        }

        if (PerStreamerK is < 0)
        {
            errors.Add("Per streamer K must be >= 0 when provided.");
        }

        SetValidationErrors(errors);
        (SubmitCommand as AsyncRelayCommand)?.RaiseCanExecuteChanged();
    }

    public List<string> ParseStreamerNames()
    {
        return StreamerNamesText
            .Split([',', '\n', '\r'], StringSplitOptions.RemoveEmptyEntries)
            .Select(name => name.Trim())
            .Where(name => !string.IsNullOrWhiteSpace(name))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    public void ApplyPrefill(Dictionary<string, string> values)
    {
        if (values.TryGetValue("current_videos_dir", out var videosDir))
        {
            CurrentVideosDir = videosDir;
        }

        if (values.TryGetValue("streamer_names", out var streamers))
        {
            StreamerNamesText = streamers;
        }
    }

    public bool HandleCancelRequest()
    {
        if (!ConfirmCancelIfDirty())
        {
            return false;
        }

        CancelRequested?.Invoke();
        return true;
    }

    public void SubmitFromShortcut()
    {
        if (SubmitCommand.CanExecute(null))
        {
            SubmitCommand.Execute(null);
        }
    }

    private async Task SubmitAsync()
    {
        Validate();
        if (HasValidationErrors)
        {
            return;
        }

        IsSubmitting = true;
        (SubmitCommand as AsyncRelayCommand)?.RaiseCanExecuteChanged();
        try
        {
            var dto = new ClipMontageJobRequestDto
            {
                StreamerNames = ParseStreamerNames(),
                CurrentVideosDir = CurrentVideosDir.Trim(),
                ApplyOverlay = ApplyOverlay,
                MaxClips = MaxClips,
                ScrapePoolSize = ScrapePoolSize,
                PerStreamerK = PerStreamerK,
            };

            var response = await _apiClient.SubmitClipMontageAsync(dto);
            FormAlert = string.Empty;
            IsDirty = false;
            Submitted?.Invoke(response.JobId);
        }
        catch (ApiException ex)
        {
            FormAlert = ex.Message;
            if (ex.ValidationErrors.Count > 0)
            {
                SetValidationErrors(ex.ValidationErrors.Select(error => error.Message));
            }
        }
        catch (HttpRequestException)
        {
            FormAlert = "Network error while submitting clip montage job.";
        }
        finally
        {
            IsSubmitting = false;
            (SubmitCommand as AsyncRelayCommand)?.RaiseCanExecuteChanged();
        }
    }
}
