using System.Collections.ObjectModel;
using TwitchClipper.Desktop.Models;

namespace TwitchClipper.Desktop.ViewModels;

public sealed class DashboardViewModel : ViewModelBase
{
    private string _healthSummary = "Checking API health...";
    private string _workerSummary = "Worker idle";

    public ObservableCollection<JobResponseDto> RecentJobs { get; } = [];

    public string HealthSummary
    {
        get => _healthSummary;
        set => SetProperty(ref _healthSummary, value);
    }

    public string WorkerSummary
    {
        get => _workerSummary;
        set => SetProperty(ref _workerSummary, value);
    }

    public void UpdateRecentJobs(IEnumerable<JobResponseDto> jobs)
    {
        RecentJobs.Clear();
        foreach (var job in jobs.Take(10))
        {
            RecentJobs.Add(job);
        }

        WorkerSummary = RecentJobs.Any(job => job.Status == "running")
            ? "Worker running"
            : "Worker idle";
    }
}
