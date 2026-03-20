/*
Test Plan
- Partitions: failed-job rendering, output-path open success, command event wiring
- Boundaries: no selected job, missing result/outputs payloads
- Failure modes: path open failure and API errors preserving user-safe messaging
# Covers: UI-IMPL-049
*/

using System.Text.Json;
using TwitchClipper.Desktop.Models;
using TwitchClipper.Desktop.ViewModels;
using TwitchClipper.Frontend.Tests.TestDoubles;

namespace TwitchClipper.Frontend.Tests;

public class JobDetailViewModelTests
{
    [Fact]
    public async Task Load_failed_job_selects_error_tab_and_builds_display_rows()
    {
        // Why: failed jobs should default to the error tab with visible payload rows.
        var api = new FakeApiClient
        {
            JobFactory = _ => Task.FromResult(new JobResponseDto
            {
                Id = "j1",
                Status = "failed",
                Error = "worker timed out while downloading",
                Result = JsonSerializer.SerializeToElement(new { reason = "timeout" }),
                Outputs = JsonSerializer.SerializeToElement(new { montage = "C:/tmp/out.mp4" }),
            })
        };
        var vm = new JobDetailViewModel(api, new RecordingPathOpener());

        await vm.LoadJobDetailAsync("j1");

        Assert.Equal(JobDetailTab.Error, vm.SelectedTab);
        Assert.Equal("worker timed out while downloading", vm.ErrorMessage);
        Assert.Contains(vm.ResultRows, row => row.Contains("reason", StringComparison.Ordinal));
        Assert.Contains(vm.OutputRows, row => row.Contains("montage", StringComparison.Ordinal));
    }

    [Fact]
    public async Task Load_job_uses_result_paths_when_outputs_payload_is_missing()
    {
        // Why: DB-disabled jobs still place output paths under result; UI should show them in outputs tab.
        var api = new FakeApiClient
        {
            JobFactory = _ => Task.FromResult(new JobResponseDto
            {
                Id = "j2",
                Status = "done",
                Result = JsonSerializer.SerializeToElement(new { montage_path = "C:/tmp/final.mp4" }),
                Outputs = null,
            })
        };
        var vm = new JobDetailViewModel(api, new RecordingPathOpener());

        await vm.LoadJobDetailAsync("j2");

        Assert.Contains(vm.OutputRows, row => row.Contains("montage_path", StringComparison.Ordinal));
        Assert.DoesNotContain(vm.OutputRows, row => row.Contains("No output paths available.", StringComparison.Ordinal));
    }

    [Fact]
    public void Open_output_path_without_job_sets_explicit_error()
    {
        // Why: opening output without a loaded job should fail safely and clearly.
        var vm = new JobDetailViewModel(new FakeApiClient(), new RecordingPathOpener());

        vm.OpenOutputPath();

        Assert.Equal("No job selected.", vm.ErrorMessage);
    }

    [Fact]
    public void Open_output_path_uses_outputs_montage_path_and_calls_path_opener()
    {
        // Why: output action should use persisted outputs payload when available.
        var opener = new RecordingPathOpener();
        var vm = new JobDetailViewModel(new FakeApiClient(), opener)
        {
            Job = new JobResponseDto
            {
                Outputs = JsonSerializer.SerializeToElement(new { montage_path = "C:/tmp/clip.mp4" }),
            }
        };

        vm.OpenOutputPath();

        Assert.Equal("C:/tmp/clip.mp4", opener.LastPath);
        Assert.Equal(string.Empty, vm.ErrorMessage);
    }

    [Fact]
    public void Open_output_path_surfaces_error_from_path_opener()
    {
        // Why: filesystem/open-shell failures must be shown to users verbatim.
        var opener = new RecordingPathOpener
        {
            Result = false,
            ErrorMessage = "The output path does not exist or cannot be accessed.",
        };
        var vm = new JobDetailViewModel(new FakeApiClient(), opener)
        {
            Job = new JobResponseDto
            {
                Result = JsonSerializer.SerializeToElement(new { montage_path = "C:/missing/file.mp4" }),
            }
        };

        vm.OpenOutputPath();

        Assert.Equal("The output path does not exist or cannot be accessed.", vm.ErrorMessage);
        Assert.Equal("C:/missing/file.mp4", opener.LastPath);
    }

    private sealed class RecordingPathOpener : TwitchClipper.Desktop.Services.IPathOpener
    {
        public bool Result { get; set; } = true;

        public string ErrorMessage { get; set; } = string.Empty;

        public string? LastPath { get; private set; }

        public bool TryOpenPath(string? path, out string errorMessage)
        {
            LastPath = path;
            errorMessage = ErrorMessage;
            return Result;
        }
    }
}
