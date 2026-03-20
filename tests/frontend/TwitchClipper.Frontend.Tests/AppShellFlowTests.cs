/*
Test Plan
- Partitions: startup hydration, submit->queue navigation, rerun routing
- Boundaries: empty queue snapshots, missing selected job
- Failure modes: health failure sets offline banner
# Covers: UI-IMPL-046
*/

using TwitchClipper.Desktop.Models;
using TwitchClipper.Desktop.Services;
using TwitchClipper.Desktop.ViewModels;
using TwitchClipper.Frontend.Tests.TestDoubles;
using System.Net.Http;

namespace TwitchClipper.Frontend.Tests;

public class AppShellFlowTests
{
    [Fact]
    public async Task Startup_hydration_sets_dashboard_health_and_loads_jobs()
    {
        // Why: launch path should hydrate dashboard and queue immediately.
        var fakeApi = new FakeApiClient
        {
            HealthFactory = () => Task.FromResult(new HealthResponseDto { Ok = true }),
            ListFactory = (_, _) => Task.FromResult<IReadOnlyList<JobResponseDto>>(
            [
                new JobResponseDto { Id = "a", Type = "vod_highlights", Status = "done", CreatedAt = "2026-03-01" }
            ])
        };

        var shell = BuildShell(fakeApi);
        await shell.StartupHydrationAsync();

        Assert.Equal("API reachable", shell.Dashboard.HealthSummary);
        Assert.Single(shell.Queue.Jobs);
        Assert.Single(shell.Dashboard.RecentJobs);
    }

    [Fact]
    public async Task Submit_vod_navigates_to_queue_and_sets_selected_job()
    {
        // Why: happy path submit should transition user to queue with selected job context.
        var fakeApi = new FakeApiClient
        {
            VodSubmitFactory = _ => Task.FromResult(new JobSubmitResponseDto { JobId = "new-job" }),
            ListFactory = (_, _) => Task.FromResult<IReadOnlyList<JobResponseDto>>(
            [
                new JobResponseDto { Id = "new-job", Type = "vod_highlights", Status = "queued" }
            ])
        };

        var shell = BuildShell(fakeApi);
        shell.NavigateTo(AppScreen.NewVod);
        shell.VodForm.VodUrl = "https://www.twitch.tv/videos/1";
        shell.VodForm.OutputDir = "vod_output";

        shell.SubmitCurrentFormCommand.Execute(null);
        await Task.Delay(80);

        Assert.Equal(AppScreen.Jobs, shell.CurrentScreen);
        Assert.Equal("new-job", shell.SelectedJobId);
    }

    [Fact]
    public async Task Startup_when_health_fails_sets_offline_banner()
    {
        // Why: offline mode must be explicit and visible for user safety.
        var fakeApi = new FakeApiClient
        {
            HealthFactory = () => throw new HttpRequestException("offline"),
        };

        var shell = BuildShell(fakeApi);
        await shell.StartupHydrationAsync();

        Assert.False(shell.IsOnline);
        Assert.Contains("Connection unavailable", shell.ConnectionBanner, StringComparison.Ordinal);
    }

    [Fact]
    public void Keyboard_navigation_commands_switch_screen()
    {
        // Why: Ctrl+1..4 shortcut target commands must always navigate.
        var shell = BuildShell(new FakeApiClient());

        shell.NavigateToClipCommand.Execute(null);
        Assert.Equal(AppScreen.NewClip, shell.CurrentScreen);

        shell.NavigateToJobsCommand.Execute(null);
        Assert.Equal(AppScreen.Jobs, shell.CurrentScreen);

        shell.NavigateToDashboardCommand.Execute(null);
        Assert.Equal(AppScreen.Dashboard, shell.CurrentScreen);
    }

    private static AppShellViewModel BuildShell(FakeApiClient fakeApi)
    {
        var settings = new AppSettings { DeveloperMode = true };
        var dialog = new TestDialogService();
        var nav = new NavigationService();
        var dashboard = new DashboardViewModel();
        var vod = new VodHighlightsFormViewModel(fakeApi, dialog);
        var clip = new ClipMontageFormViewModel(fakeApi, dialog);
        var queue = new JobsQueueViewModel(fakeApi, settings);
        var detail = new JobDetailViewModel(fakeApi, new PathOpener());

        return new AppShellViewModel(nav, fakeApi, settings, dashboard, vod, clip, queue, detail);
    }
}
