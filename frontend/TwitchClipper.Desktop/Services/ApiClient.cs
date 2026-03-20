using System.Net;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using TwitchClipper.Desktop.Models;

namespace TwitchClipper.Desktop.Services;

public interface IApiClient
{
    Task<HealthResponseDto> GetHealthAsync(CancellationToken cancellationToken = default);

    Task<JobSubmitResponseDto> SubmitVodHighlightsAsync(
        VodHighlightsJobRequestDto request,
        CancellationToken cancellationToken = default);

    Task<JobSubmitResponseDto> SubmitClipMontageAsync(
        ClipMontageJobRequestDto request,
        CancellationToken cancellationToken = default);

    Task<JobResponseDto> GetJobAsync(string jobId, CancellationToken cancellationToken = default);

    Task<IReadOnlyList<JobResponseDto>> ListJobsAsync(
        string? status = null,
        int limit = 100,
        CancellationToken cancellationToken = default);

    Task<RunNextResponseDto> RunNextAsync(CancellationToken cancellationToken = default);
}

public sealed class ApiClient : IApiClient
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DictionaryKeyPolicy = JsonNamingPolicy.SnakeCaseLower,
    };

    private readonly HttpClient _httpClient;
    private readonly IApiErrorMapper _errorMapper;

    public ApiClient(HttpClient httpClient, IApiErrorMapper errorMapper)
    {
        _httpClient = httpClient;
        _errorMapper = errorMapper;
    }

    public async Task<HealthResponseDto> GetHealthAsync(CancellationToken cancellationToken = default)
    {
        var response = await _httpClient.GetAsync("/health", cancellationToken);
        await EnsureSuccess(response);
        return await ReadRequired<HealthResponseDto>(response, cancellationToken);
    }

    public async Task<JobSubmitResponseDto> SubmitVodHighlightsAsync(
        VodHighlightsJobRequestDto request,
        CancellationToken cancellationToken = default)
    {
        var response = await _httpClient.PostAsync(
            "/jobs/vod-highlights",
            BuildJsonContent(request),
            cancellationToken);
        await EnsureSuccess(response);
        return await ReadRequired<JobSubmitResponseDto>(response, cancellationToken);
    }

    public async Task<JobSubmitResponseDto> SubmitClipMontageAsync(
        ClipMontageJobRequestDto request,
        CancellationToken cancellationToken = default)
    {
        var response = await _httpClient.PostAsync(
            "/jobs/clip-montage",
            BuildJsonContent(request),
            cancellationToken);
        await EnsureSuccess(response);
        return await ReadRequired<JobSubmitResponseDto>(response, cancellationToken);
    }

    public async Task<JobResponseDto> GetJobAsync(string jobId, CancellationToken cancellationToken = default)
    {
        var response = await _httpClient.GetAsync($"/jobs/{jobId}", cancellationToken);
        await EnsureSuccess(response);
        return await ReadRequired<JobResponseDto>(response, cancellationToken);
    }

    public async Task<IReadOnlyList<JobResponseDto>> ListJobsAsync(
        string? status = null,
        int limit = 100,
        CancellationToken cancellationToken = default)
    {
        var query = string.IsNullOrWhiteSpace(status)
            ? $"/jobs?limit={limit}"
            : $"/jobs?status={Uri.EscapeDataString(status)}&limit={limit}";
        var response = await _httpClient.GetAsync(query, cancellationToken);
        await EnsureSuccess(response);
        return await ReadRequired<List<JobResponseDto>>(response, cancellationToken);
    }

    public async Task<RunNextResponseDto> RunNextAsync(CancellationToken cancellationToken = default)
    {
        var response = await _httpClient.PostAsync(
            "/jobs/run-next",
            BuildJsonContent(new { }),
            cancellationToken);
        await EnsureSuccess(response);
        var payload = await ReadRequired<RunNextResponseDto>(response, cancellationToken);
        if (!payload.IsUnionValid())
        {
            throw new ApiException(HttpStatusCode.InternalServerError, "Invalid run-next response shape.");
        }

        return payload;
    }

    private static StringContent BuildJsonContent<T>(T payload)
    {
        return new StringContent(
            JsonSerializer.Serialize(payload, JsonOptions),
            Encoding.UTF8,
            "application/json");
    }

    private async Task EnsureSuccess(HttpResponseMessage response)
    {
        if (response.IsSuccessStatusCode)
        {
            return;
        }

        throw await _errorMapper.MapFromResponseAsync(response);
    }

    private static async Task<T> ReadRequired<T>(
        HttpResponseMessage response,
        CancellationToken cancellationToken)
    {
        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        var payload = await JsonSerializer.DeserializeAsync<T>(stream, JsonOptions, cancellationToken);
        if (payload is null)
        {
            throw new ApiException(HttpStatusCode.InternalServerError, "Empty response payload.");
        }

        return payload;
    }
}
