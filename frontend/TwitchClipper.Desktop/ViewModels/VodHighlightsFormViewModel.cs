using System.Windows.Input;
using System.Net.Http;
using TwitchClipper.Desktop.Commands;
using TwitchClipper.Desktop.Models;
using TwitchClipper.Desktop.Services;

namespace TwitchClipper.Desktop.ViewModels;

public sealed class VodHighlightsFormViewModel : FormViewModelBase
{
    private readonly IApiClient _apiClient;

    private string _vodUrl = string.Empty;
    private string _outputDir = "vod_output";
    private string _chatPath = string.Empty;
    private string _keywordsText = string.Empty;
    private int _minCount = 3;
    private int _spikeWindowSeconds = 30;
    private int _segmentPaddingSeconds = 12;
    private double _maxSegmentSeconds = 120;
    private int _diversityWindows = 8;
    private string _formAlert = string.Empty;

    public VodHighlightsFormViewModel(IApiClient apiClient, IDialogService dialogService)
        : base(dialogService)
    {
        _apiClient = apiClient;

        SubmitCommand = new AsyncRelayCommand(_ => SubmitAsync(), _ => CanSubmit);
        ResetDefaultsCommand = new RelayCommand(_ => ResetDefaults());
        CancelCommand = new RelayCommand(_ => CancelRequested?.Invoke());
    }

    public event Action<string>? Submitted;

    public event Action? CancelRequested;

    public ICommand SubmitCommand { get; }

    public ICommand ResetDefaultsCommand { get; }

    public ICommand CancelCommand { get; }

    public string VodUrl
    {
        get => _vodUrl;
        set
        {
            if (SetProperty(ref _vodUrl, value))
            {
                MarkDirty();
                Validate();
            }
        }
    }

    public string OutputDir
    {
        get => _outputDir;
        set
        {
            if (SetProperty(ref _outputDir, value))
            {
                MarkDirty();
                Validate();
            }
        }
    }

    public string ChatPath
    {
        get => _chatPath;
        set
        {
            if (SetProperty(ref _chatPath, value))
            {
                MarkDirty();
                Validate();
            }
        }
    }

    public string KeywordsText
    {
        get => _keywordsText;
        set
        {
            if (SetProperty(ref _keywordsText, value))
            {
                MarkDirty();
                Validate();
            }
        }
    }

    public int MinCount
    {
        get => _minCount;
        set
        {
            if (SetProperty(ref _minCount, value))
            {
                MarkDirty();
                Validate();
            }
        }
    }

    public int SpikeWindowSeconds
    {
        get => _spikeWindowSeconds;
        set
        {
            if (SetProperty(ref _spikeWindowSeconds, value))
            {
                MarkDirty();
                Validate();
            }
        }
    }

    public int SegmentPaddingSeconds
    {
        get => _segmentPaddingSeconds;
        set
        {
            if (SetProperty(ref _segmentPaddingSeconds, value))
            {
                MarkDirty();
                Validate();
            }
        }
    }

    public double MaxSegmentSeconds
    {
        get => _maxSegmentSeconds;
        set
        {
            if (SetProperty(ref _maxSegmentSeconds, value))
            {
                MarkDirty();
                Validate();
            }
        }
    }

    public int DiversityWindows
    {
        get => _diversityWindows;
        set
        {
            if (SetProperty(ref _diversityWindows, value))
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
        if (string.IsNullOrWhiteSpace(VodUrl))
        {
            errors.Add("VOD URL is required.");
        }

        if (string.IsNullOrWhiteSpace(OutputDir))
        {
            errors.Add("Output directory is required.");
        }

        if (MinCount < 1)
        {
            errors.Add("Min count must be >= 1.");
        }

        if (SpikeWindowSeconds <= 0)
        {
            errors.Add("Spike window seconds must be > 0.");
        }

        if (SegmentPaddingSeconds < 0)
        {
            errors.Add("Segment padding seconds must be >= 0.");
        }

        if (MaxSegmentSeconds <= 0)
        {
            errors.Add("Max segment seconds must be > 0.");
        }

        if (DiversityWindows < 1)
        {
            errors.Add("Diversity windows must be >= 1.");
        }

        SetValidationErrors(errors);
        (SubmitCommand as AsyncRelayCommand)?.RaiseCanExecuteChanged();
    }

    public void ResetDefaults()
    {
        MinCount = 3;
        SpikeWindowSeconds = 30;
        SegmentPaddingSeconds = 12;
        MaxSegmentSeconds = 120;
        DiversityWindows = 8;
    }

    public void ApplyPrefill(Dictionary<string, string> values)
    {
        if (values.TryGetValue("vod_url", out var vodUrl))
        {
            VodUrl = vodUrl;
        }

        if (values.TryGetValue("output_dir", out var outputDir))
        {
            OutputDir = outputDir;
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
            var dto = new VodHighlightsJobRequestDto
            {
                VodUrl = VodUrl.Trim(),
                OutputDir = OutputDir.Trim(),
                ChatPath = string.IsNullOrWhiteSpace(ChatPath) ? null : ChatPath.Trim(),
                Keywords = KeywordsText
                    .Split(',', StringSplitOptions.RemoveEmptyEntries)
                    .Select(keyword => keyword.Trim())
                    .Where(keyword => !string.IsNullOrWhiteSpace(keyword))
                    .ToList(),
                MinCount = MinCount,
                SpikeWindowSeconds = SpikeWindowSeconds,
                SegmentPaddingSeconds = SegmentPaddingSeconds,
                MaxSegmentSeconds = MaxSegmentSeconds,
                DiversityWindows = DiversityWindows,
            };

            var response = await _apiClient.SubmitVodHighlightsAsync(dto);
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
            FormAlert = "Network error while submitting VOD job.";
        }
        finally
        {
            IsSubmitting = false;
            (SubmitCommand as AsyncRelayCommand)?.RaiseCanExecuteChanged();
        }
    }
}
