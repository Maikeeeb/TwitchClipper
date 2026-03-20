using System.Text.Json;
using System.Windows.Input;
using TwitchClipper.Desktop.Commands;
using TwitchClipper.Desktop.Models;
using TwitchClipper.Desktop.Services;

namespace TwitchClipper.Desktop.ViewModels;

public sealed class AppShellViewModel : ViewModelBase
{
    private readonly INavigationService _navigationService;
    private readonly IApiClient _apiClient;
    private readonly AppSettings _settings;

    private AppScreen _currentScreen;
    private string? _selectedJobId;
    private bool _isOnline = true;
    private DateTimeOffset? _lastHealthCheckAt;
    private string _connectionBanner = string.Empty;

    public AppShellViewModel(
        INavigationService navigationService,
        IApiClient apiClient,
        AppSettings settings,
        DashboardViewModel dashboardViewModel,
        VodHighlightsFormViewModel vodFormViewModel,
        ClipMontageFormViewModel clipFormViewModel,
        JobsQueueViewModel queueViewModel,
        JobDetailViewModel detailViewModel)
    {
        _navigationService = navigationService;
        _apiClient = apiClient;
        _settings = settings;

        Dashboard = dashboardViewModel;
        VodForm = vodFormViewModel;
        ClipForm = clipFormViewModel;
        Queue = queueViewModel;
        Detail = detailViewModel;

        _currentScreen = _navigationService.CurrentScreen;
        _navigationService.ScreenChanged += (_, screen) => CurrentScreen = screen;

        NavigateToDashboardCommand = new RelayCommand(_ => NavigateTo(AppScreen.Dashboard));
        NavigateToVodCommand = new RelayCommand(_ => NavigateTo(AppScreen.NewVod));
        NavigateToClipCommand = new RelayCommand(_ => NavigateTo(AppScreen.NewClip));
        NavigateToJobsCommand = new RelayCommand(_ => NavigateTo(AppScreen.Jobs));
        BackCommand = new RelayCommand(_ => NavigateBack());
        RefreshHealthCommand = new AsyncRelayCommand(_ => RefreshHealthAsync());
        SubmitCurrentFormCommand = new RelayCommand(_ => SubmitCurrentForm());
        RefreshCurrentScreenCommand = new AsyncRelayCommand(_ => RefreshCurrentScreenAsync());
        CancelCurrentActionCommand = new RelayCommand(_ => CancelCurrentAction());

        Queue.JobSelected += async jobId =>
        {
            SelectedJobId = jobId;
            await Detail.LoadJobDetailAsync(jobId);
            NavigateTo(AppScreen.JobDetail);
        };

        Detail.BackRequested += () => NavigateTo(AppScreen.Jobs);
        Detail.RerunRequested += HandleRerunRequested;

        VodForm.Submitted += async jobId =>
        {
            SelectedJobId = jobId;
            NavigateTo(AppScreen.Jobs);
            await Queue.RefreshJobsAsync();
        };
        VodForm.CancelRequested += () => NavigateTo(AppScreen.Dashboard);

        ClipForm.Submitted += async jobId =>
        {
            SelectedJobId = jobId;
            NavigateTo(AppScreen.Jobs);
            await Queue.RefreshJobsAsync();
        };
        ClipForm.CancelRequested += () => NavigateTo(AppScreen.Dashboard);
    }

    public DashboardViewModel Dashboard { get; }

    public VodHighlightsFormViewModel VodForm { get; }

    public ClipMontageFormViewModel ClipForm { get; }

    public JobsQueueViewModel Queue { get; }

    public JobDetailViewModel Detail { get; }

    public ICommand NavigateToDashboardCommand { get; }

    public ICommand NavigateToVodCommand { get; }

    public ICommand NavigateToClipCommand { get; }

    public ICommand NavigateToJobsCommand { get; }

    public ICommand BackCommand { get; }

    public ICommand RefreshHealthCommand { get; }

    public ICommand SubmitCurrentFormCommand { get; }

    public ICommand RefreshCurrentScreenCommand { get; }

    public ICommand CancelCurrentActionCommand { get; }

    public bool DeveloperMode => _settings.DeveloperMode;

    public AppScreen CurrentScreen
    {
        get => _currentScreen;
        set => SetProperty(ref _currentScreen, value);
    }

    public string? SelectedJobId
    {
        get => _selectedJobId;
        set => SetProperty(ref _selectedJobId, value);
    }

    public bool IsOnline
    {
        get => _isOnline;
        set => SetProperty(ref _isOnline, value);
    }

    public DateTimeOffset? LastHealthCheckAt
    {
        get => _lastHealthCheckAt;
        set => SetProperty(ref _lastHealthCheckAt, value);
    }

    public string ConnectionBanner
    {
        get => _connectionBanner;
        set => SetProperty(ref _connectionBanner, value);
    }

    public object CurrentScreenViewModel => CurrentScreen switch
    {
        AppScreen.Dashboard => Dashboard,
        AppScreen.NewVod => VodForm,
        AppScreen.NewClip => ClipForm,
        AppScreen.Jobs => Queue,
        AppScreen.JobDetail => Detail,
        _ => Dashboard,
    };

    public async Task StartupHydrationAsync()
    {
        await RefreshHealthAsync();
        await Queue.RefreshJobsAsync();
        Dashboard.UpdateRecentJobs(Queue.Jobs.Take(10));
        Queue.StartPolling();
    }

    public void NavigateTo(AppScreen screen)
    {
        _navigationService.NavigateTo(screen);
        OnPropertyChanged(nameof(CurrentScreenViewModel));
    }

    private void NavigateBack()
    {
        if (CurrentScreen == AppScreen.JobDetail)
        {
            NavigateTo(AppScreen.Jobs);
            return;
        }

        NavigateTo(AppScreen.Dashboard);
    }

    private async Task RefreshHealthAsync()
    {
        try
        {
            var response = await _apiClient.GetHealthAsync();
            LastHealthCheckAt = DateTimeOffset.Now;
            IsOnline = response.Ok;
            ConnectionBanner = response.Ok ? string.Empty : "Connection unavailable. Retrying in 5 seconds.";
            Dashboard.HealthSummary = response.Ok ? "API reachable" : "API unavailable";
        }
        catch (Exception)
        {
            LastHealthCheckAt = DateTimeOffset.Now;
            IsOnline = false;
            ConnectionBanner = "Connection unavailable. Retrying in 5 seconds.";
            Dashboard.HealthSummary = "API unavailable";
        }
    }

    private async Task RefreshCurrentScreenAsync()
    {
        if (CurrentScreen is AppScreen.Jobs or AppScreen.JobDetail)
        {
            await Queue.RefreshJobsAsync();
            if (!string.IsNullOrWhiteSpace(SelectedJobId))
            {
                await Detail.LoadJobDetailAsync(SelectedJobId);
            }
        }

        await RefreshHealthAsync();
        Dashboard.UpdateRecentJobs(Queue.Jobs.Take(10));
    }

    private void SubmitCurrentForm()
    {
        if (CurrentScreen == AppScreen.NewVod)
        {
            VodForm.SubmitFromShortcut();
        }
        else if (CurrentScreen == AppScreen.NewClip)
        {
            ClipForm.SubmitFromShortcut();
        }
    }

    private void CancelCurrentAction()
    {
        if (CurrentScreen == AppScreen.NewVod)
        {
            VodForm.HandleCancelRequest();
        }
        else if (CurrentScreen == AppScreen.NewClip)
        {
            ClipForm.HandleCancelRequest();
        }
    }

    private void HandleRerunRequested(JobResponseDto? job)
    {
        if (job is null)
        {
            return;
        }

        var values = new Dictionary<string, string>();
        foreach (var item in job.Params)
        {
            values[item.Key] = item.Value.ValueKind == JsonValueKind.Array
                ? string.Join(", ", item.Value.EnumerateArray().Where(value => value.ValueKind == JsonValueKind.String).Select(value => value.GetString()))
                : item.Value.ToString();
        }

        if (string.Equals(job.Type, "vod_highlights", StringComparison.OrdinalIgnoreCase))
        {
            VodForm.ApplyPrefill(values);
            NavigateTo(AppScreen.NewVod);
        }
        else
        {
            ClipForm.ApplyPrefill(values);
            NavigateTo(AppScreen.NewClip);
        }
    }
}
