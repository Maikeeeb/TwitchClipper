using System.Collections.ObjectModel;
using System.Windows.Input;
using System.Windows.Threading;
using TwitchClipper.Desktop.Commands;
using TwitchClipper.Desktop.Models;
using TwitchClipper.Desktop.Services;

namespace TwitchClipper.Desktop.ViewModels;

public sealed class JobsQueueViewModel : ViewModelBase
{
    private readonly IApiClient _apiClient;
    private readonly AppSettings _appSettings;
    private readonly DispatcherTimer _pollTimer;

    private readonly List<JobResponseDto> _allJobs = [];

    private string _statusFilter = "all";
    private string _searchText = string.Empty;
    private bool _isPolling;
    private DateTimeOffset? _lastRefreshAt;
    private string _bannerError = string.Empty;
    private bool _isOffline;
    private int _retrySeconds;
    private JobResponseDto? _selectedJob;

    public JobsQueueViewModel(IApiClient apiClient, AppSettings appSettings)
    {
        _apiClient = apiClient;
        _appSettings = appSettings;

        _retrySeconds = _appSettings.OfflineRetryBaseSeconds;

        Jobs = [];
        RefreshCommand = new AsyncRelayCommand(_ => RefreshJobsAsync());
        RunNextCommand = new AsyncRelayCommand(_ => RunNextAsync(), _ => _appSettings.DeveloperMode);
        OpenSelectedJobCommand = new RelayCommand(_ => OpenSelectedJob(), _ => SelectedJob is not null);

        _pollTimer = new DispatcherTimer
        {
            Interval = TimeSpan.FromMilliseconds(_appSettings.PollingIntervalMs),
        };
        _pollTimer.Tick += async (_, _) => await RefreshJobsAsync();
    }

    public event Action<string>? JobSelected;

    public ObservableCollection<JobResponseDto> Jobs { get; }

    public ICommand RefreshCommand { get; }

    public ICommand RunNextCommand { get; }

    public ICommand OpenSelectedJobCommand { get; }

    public JobResponseDto? SelectedJob
    {
        get => _selectedJob;
        set
        {
            if (SetProperty(ref _selectedJob, value))
            {
                (OpenSelectedJobCommand as RelayCommand)?.RaiseCanExecuteChanged();
            }
        }
    }

    public string StatusFilter
    {
        get => _statusFilter;
        set
        {
            if (SetProperty(ref _statusFilter, value))
            {
                ApplyFilters();
            }
        }
    }

    public string SearchText
    {
        get => _searchText;
        set
        {
            if (SetProperty(ref _searchText, value))
            {
                ApplyFilters();
            }
        }
    }

    public bool IsPolling
    {
        get => _isPolling;
        set => SetProperty(ref _isPolling, value);
    }

    public DateTimeOffset? LastRefreshAt
    {
        get => _lastRefreshAt;
        set => SetProperty(ref _lastRefreshAt, value);
    }

    public string BannerError
    {
        get => _bannerError;
        set => SetProperty(ref _bannerError, value);
    }

    public bool IsOffline
    {
        get => _isOffline;
        set => SetProperty(ref _isOffline, value);
    }

    public void StartPolling()
    {
        if (_pollTimer.IsEnabled)
        {
            return;
        }

        IsPolling = true;
        _pollTimer.Start();
    }

    public void StopPolling()
    {
        IsPolling = false;
        _pollTimer.Stop();
    }

    public async Task RefreshJobsAsync()
    {
        try
        {
            if (IsOffline)
            {
                var health = await _apiClient.GetHealthAsync();
                if (health.Ok)
                {
                    IsOffline = false;
                    BannerError = string.Empty;
                    _retrySeconds = _appSettings.OfflineRetryBaseSeconds;
                }
            }

            var jobs = await _apiClient.ListJobsAsync(limit: 200);
            _allJobs.Clear();
            _allJobs.AddRange(jobs.OrderByDescending(job => job.CreatedAt));
            ApplyFilters();
            LastRefreshAt = DateTimeOffset.Now;
            BannerError = string.Empty;
        }
        catch (ApiException ex) when (ex.StatusCode == System.Net.HttpStatusCode.NotFound)
        {
            BannerError = "A job became stale and could not be loaded.";
        }
        catch (Exception)
        {
            IsOffline = true;
            BannerError = $"Connection unavailable. Retrying in {_retrySeconds} seconds.";
            _pollTimer.Interval = TimeSpan.FromSeconds(_retrySeconds);
            _retrySeconds = Math.Min(_retrySeconds * 2, _appSettings.OfflineRetryMaxSeconds);
        }
    }

    public async Task RunNextAsync()
    {
        try
        {
            var result = await _apiClient.RunNextAsync();
            if (result.Processed == 0)
            {
                BannerError = "No queued jobs to process.";
            }

            await RefreshJobsAsync();
        }
        catch (Exception)
        {
            BannerError = "Run-next request failed.";
        }
    }

    public void OpenSelectedJob()
    {
        if (SelectedJob is null)
        {
            return;
        }

        JobSelected?.Invoke(SelectedJob.Id);
    }

    private void ApplyFilters()
    {
        Jobs.Clear();

        var query = _allJobs.AsEnumerable();
        if (!string.Equals(StatusFilter, "all", StringComparison.OrdinalIgnoreCase))
        {
            query = query.Where(job => string.Equals(job.Status, StatusFilter, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(SearchText))
        {
            query = query.Where(job => job.Id.Contains(SearchText, StringComparison.OrdinalIgnoreCase));
        }

        foreach (var job in query)
        {
            Jobs.Add(job);
        }

        if (SelectedJob is not null)
        {
            SelectedJob = Jobs.FirstOrDefault(job => job.Id == SelectedJob.Id);
        }

        (OpenSelectedJobCommand as RelayCommand)?.RaiseCanExecuteChanged();
    }
}
