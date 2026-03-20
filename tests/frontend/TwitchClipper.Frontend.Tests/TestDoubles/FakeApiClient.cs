using TwitchClipper.Desktop.Models;
using TwitchClipper.Desktop.Services;

namespace TwitchClipper.Frontend.Tests.TestDoubles;

public sealed class FakeApiClient : IApiClient
{
    public Func<Task<HealthResponseDto>>? HealthFactory { get; set; }

    public Func<VodHighlightsJobRequestDto, Task<JobSubmitResponseDto>>? VodSubmitFactory { get; set; }

    public Func<ClipMontageJobRequestDto, Task<JobSubmitResponseDto>>? ClipSubmitFactory { get; set; }

    public Func<string, Task<JobResponseDto>>? JobFactory { get; set; }

    public Func<string?, int, Task<IReadOnlyList<JobResponseDto>>>? ListFactory { get; set; }

    public Func<Task<RunNextResponseDto>>? RunNextFactory { get; set; }

    public Task<HealthResponseDto> GetHealthAsync(CancellationToken cancellationToken = default)
    {
        return HealthFactory?.Invoke() ?? Task.FromResult(new HealthResponseDto { Ok = true });
    }

    public Task<JobSubmitResponseDto> SubmitVodHighlightsAsync(
        VodHighlightsJobRequestDto request,
        CancellationToken cancellationToken = default)
    {
        return VodSubmitFactory?.Invoke(request)
            ?? Task.FromResult(new JobSubmitResponseDto { JobId = Guid.NewGuid().ToString() });
    }

    public Task<JobSubmitResponseDto> SubmitClipMontageAsync(
        ClipMontageJobRequestDto request,
        CancellationToken cancellationToken = default)
    {
        return ClipSubmitFactory?.Invoke(request)
            ?? Task.FromResult(new JobSubmitResponseDto { JobId = Guid.NewGuid().ToString() });
    }

    public Task<JobResponseDto> GetJobAsync(string jobId, CancellationToken cancellationToken = default)
    {
        return JobFactory?.Invoke(jobId)
            ?? Task.FromResult(new JobResponseDto { Id = jobId, Type = "vod_highlights", Status = "queued" });
    }

    public Task<IReadOnlyList<JobResponseDto>> ListJobsAsync(
        string? status = null,
        int limit = 100,
        CancellationToken cancellationToken = default)
    {
        return ListFactory?.Invoke(status, limit)
            ?? Task.FromResult<IReadOnlyList<JobResponseDto>>([]);
    }

    public Task<RunNextResponseDto> RunNextAsync(CancellationToken cancellationToken = default)
    {
        return RunNextFactory?.Invoke() ?? Task.FromResult(new RunNextResponseDto { Processed = 0 });
    }
}
