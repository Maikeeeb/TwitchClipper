/*
Test Plan
- Partitions: successful refresh, stale-job API error, run-next failure path, selected-row navigation
- Boundaries: empty job list, "all" vs explicit status filter, repeated filter updates
- Failure modes: offline recovery handshake and run-next exception fallback
# Covers: UI-IMPL-048
*/

using System.Net;
using TwitchClipper.Desktop.Commands;
using TwitchClipper.Desktop.Models;
using TwitchClipper.Desktop.Services;
using TwitchClipper.Desktop.ViewModels;
using TwitchClipper.Frontend.Tests.TestDoubles;

namespace TwitchClipper.Frontend.Tests;

public class JobsQueueViewModelTests
{
    [Fact]
    public void Start_and_stop_polling_toggle_state_flag()
    {
        // Why: polling state drives visibility and timer lifecycle in queue view.
        var vm = new JobsQueueViewModel(new FakeApiClient(), new AppSettings());

        vm.StartPolling();
        Assert.True(vm.IsPolling);

        vm.StopPolling();
        Assert.False(vm.IsPolling);
    }

    [Fact]
    public async Task Refresh_applies_status_and_search_filters_and_preserves_selected_job()
    {
        // Why: queue filtering is core navigation behavior and must keep selection stable.
        var api = new FakeApiClient
        {
            ListFactory = (_, _) => Task.FromResult<IReadOnlyList<JobResponseDto>>(
            [
                new JobResponseDto { Id = "match-1", Status = "queued", CreatedAt = "2026-03-02T10:00:00Z" },
                new JobResponseDto { Id = "other-2", Status = "done", CreatedAt = "2026-03-01T10:00:00Z" }
            ])
        };
        var vm = new JobsQueueViewModel(api, new AppSettings());

        await vm.RefreshJobsAsync();
        vm.SelectedJob = vm.Jobs.First(job => job.Id == "match-1");
        vm.StatusFilter = "queued";
        vm.SearchText = "match";

        Assert.Single(vm.Jobs);
        Assert.Equal("match-1", vm.Jobs[0].Id);
        Assert.Equal("match-1", vm.SelectedJob?.Id);
    }

    [Fact]
    public async Task Refresh_not_found_sets_stale_job_banner()
    {
        // Why: stale rows should produce a precise remediation message.
        var api = new FakeApiClient
        {
            ListFactory = (_, _) => throw new ApiException(HttpStatusCode.NotFound, "gone"),
        };
        var vm = new JobsQueueViewModel(api, new AppSettings());

        await vm.RefreshJobsAsync();

        Assert.Equal("A job became stale and could not be loaded.", vm.BannerError);
    }

    [Fact]
    public async Task Refresh_while_offline_recovers_on_successful_health_check()
    {
        // Why: offline mode must recover cleanly when health endpoint comes back.
        var api = new FakeApiClient
        {
            HealthFactory = () => Task.FromResult(new HealthResponseDto { Ok = true }),
            ListFactory = (_, _) => Task.FromResult<IReadOnlyList<JobResponseDto>>([]),
        };
        var vm = new JobsQueueViewModel(api, new AppSettings());
        vm.IsOffline = true;
        vm.BannerError = "Connection unavailable. Retrying in 5 seconds.";

        await vm.RefreshJobsAsync();

        Assert.False(vm.IsOffline);
        Assert.Equal(string.Empty, vm.BannerError);
    }

    [Fact]
    public async Task Run_next_failure_sets_fallback_banner()
    {
        // Why: operator-triggered run-next failures must surface a deterministic fallback message.
        var api = new FakeApiClient
        {
            RunNextFactory = () => throw new HttpRequestException("offline"),
        };
        var vm = new JobsQueueViewModel(api, new AppSettings { DeveloperMode = true });

        await vm.RunNextAsync();

        Assert.Equal("Run-next request failed.", vm.BannerError);
    }

    [Fact]
    public void Open_selected_job_raises_event_with_selected_job_id()
    {
        // Why: selecting a queue row should route to job detail with stable id.
        var vm = new JobsQueueViewModel(new FakeApiClient(), new AppSettings())
        {
            SelectedJob = new JobResponseDto { Id = "job-42" },
        };
        string? selected = null;
        vm.JobSelected += id => selected = id;

        vm.OpenSelectedJob();

        Assert.Equal("job-42", selected);
    }

    [Fact]
    public void Open_selected_command_can_execute_tracks_selection_changes()
    {
        // Why: queue row selection must immediately enable open-selected action.
        var vm = new JobsQueueViewModel(new FakeApiClient(), new AppSettings());
        var command = Assert.IsType<RelayCommand>(vm.OpenSelectedJobCommand);

        Assert.False(command.CanExecute(null));

        vm.SelectedJob = new JobResponseDto { Id = "job-1" };
        Assert.True(command.CanExecute(null));

        vm.SelectedJob = null;
        Assert.False(command.CanExecute(null));
    }

    [Fact]
    public async Task Filter_updates_remain_consistent_across_repeated_changes()
    {
        // Why: repeated UI typing should not corrupt queue state over time.
        var api = new FakeApiClient
        {
            ListFactory = (_, _) => Task.FromResult<IReadOnlyList<JobResponseDto>>(
            [
                new JobResponseDto { Id = "alpha-1", Status = "queued", CreatedAt = "2026-03-02" },
                new JobResponseDto { Id = "beta-2", Status = "queued", CreatedAt = "2026-03-01" }
            ])
        };
        var vm = new JobsQueueViewModel(api, new AppSettings());
        await vm.RefreshJobsAsync();
        vm.StatusFilter = "queued";

        for (var i = 0; i < 100; i++)
        {
            vm.SearchText = i % 2 == 0 ? "alpha" : "beta";
            Assert.Single(vm.Jobs);
        }

        vm.SearchText = "alpha";
        Assert.Equal("alpha-1", vm.Jobs.Single().Id);
    }
}
