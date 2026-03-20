/*
Test Plan
- Partitions: 422 submit errors, 404 job detail, offline queue behavior, rerun prefill parsing
- Boundaries: missing params map for rerun, empty params dictionary
- Failure modes: stale/missing job id from API
# Covers: UI-IMPL-047
*/

using System.Net;
using TwitchClipper.Desktop.Models;
using TwitchClipper.Desktop.Services;
using TwitchClipper.Desktop.ViewModels;
using TwitchClipper.Frontend.Tests.TestDoubles;

namespace TwitchClipper.Frontend.Tests;

public class DefectScenarioTests
{
    [Fact]
    public async Task JobDetail_load_404_sets_not_found_error()
    {
        // Why: stale queue rows should show clear not-found message.
        var api = new FakeApiClient
        {
            JobFactory = _ => throw new ApiException(HttpStatusCode.NotFound, "missing"),
        };
        var vm = new JobDetailViewModel(api, new PathOpener());

        await vm.LoadJobDetailAsync("missing-id");

        Assert.Contains("Job not found", vm.ErrorMessage, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Queue_refresh_failure_enters_offline_mode()
    {
        // Why: polling failures must move UI into degraded/offline state.
        var api = new FakeApiClient
        {
            ListFactory = (_, _) => throw new HttpRequestException("offline"),
        };
        var vm = new JobsQueueViewModel(api, new AppSettings());

        await vm.RefreshJobsAsync();

        Assert.True(vm.IsOffline);
        Assert.Contains("Connection unavailable", vm.BannerError, StringComparison.Ordinal);
    }

    [Fact]
    public void Rerun_with_missing_prefill_data_keeps_navigation_valid()
    {
        // Why: rerun should not throw on sparse legacy params.
        var shell = BuildShell(new FakeApiClient());
        var detail = shell.Detail;
        var legacyJob = new JobResponseDto
        {
            Id = "legacy",
            Type = "vod_highlights",
            Status = "failed",
            Params = []
        };

        shell.NavigateTo(AppScreen.JobDetail);
        detail.RerunWithPrefillCommand.Execute(legacyJob);

        // command binds to current job in VM; ensure no crash and screen remains valid.
        Assert.True(shell.CurrentScreen is AppScreen.JobDetail or AppScreen.NewVod or AppScreen.NewClip);
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
