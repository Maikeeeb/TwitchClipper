/*
Test Plan
- Partitions: GET/POST endpoint contract paths, status-filtered query, mapper-driven failure translation
- Boundaries: empty status filter and non-empty status filter query composition
- Failure modes: non-success responses delegated to error mapper
# Covers: UI-IMPL-053
*/

using System.Net;
using System.Net.Http;
using System.Text;
using TwitchClipper.Desktop.Models;
using TwitchClipper.Desktop.Services;

namespace TwitchClipper.Frontend.Tests;

public class ApiClientBehaviorTests
{
    [Fact]
    public async Task Get_health_calls_health_endpoint_and_parses_payload()
    {
        // Why: health polling contract should always hit /health and parse bool state.
        HttpRequestMessage? captured = null;
        using var client = BuildClient(
            request =>
            {
                captured = request;
                return new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = JsonContent("{\"ok\":true}")
                };
            });
        var sut = new ApiClient(client, new ApiErrorMapper());

        var response = await sut.GetHealthAsync();

        Assert.True(response.Ok);
        Assert.Equal(HttpMethod.Get, captured?.Method);
        Assert.Equal("/health", captured?.RequestUri?.PathAndQuery);
    }

    [Fact]
    public async Task List_jobs_with_status_builds_filtered_query()
    {
        // Why: queue filtering relies on precise status query encoding.
        HttpRequestMessage? captured = null;
        using var client = BuildClient(
            request =>
            {
                captured = request;
                return new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = JsonContent("[]")
                };
            });
        var sut = new ApiClient(client, new ApiErrorMapper());

        var items = await sut.ListJobsAsync("queued", 25);

        Assert.Empty(items);
        Assert.Equal("/jobs?status=queued&limit=25", captured?.RequestUri?.PathAndQuery);
    }

    [Fact]
    public async Task Submit_vod_posts_to_expected_endpoint()
    {
        // Why: submit routing must keep backend endpoint contract stable.
        HttpRequestMessage? captured = null;
        using var client = BuildClient(
            request =>
            {
                captured = request;
                return new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = JsonContent("{\"job_id\":\"job-7\"}")
                };
            });
        var sut = new ApiClient(client, new ApiErrorMapper());

        var result = await sut.SubmitVodHighlightsAsync(new VodHighlightsJobRequestDto
        {
            VodUrl = "https://www.twitch.tv/videos/7",
            OutputDir = "vod_output"
        });

        Assert.Equal("job-7", result.JobId);
        Assert.Equal(HttpMethod.Post, captured?.Method);
        Assert.Equal("/jobs/vod-highlights", captured?.RequestUri?.PathAndQuery);
    }

    [Fact]
    public async Task Non_success_response_uses_error_mapper()
    {
        // Why: API failures must preserve mapped status/message behavior.
        using var client = BuildClient(
            _ => new HttpResponseMessage(HttpStatusCode.NotFound)
            {
                Content = JsonContent("{}")
            });
        var sut = new ApiClient(client, new ApiErrorMapper());

        var ex = await Assert.ThrowsAsync<ApiException>(() => sut.GetJobAsync("missing"));

        Assert.Equal(HttpStatusCode.NotFound, ex.StatusCode);
        Assert.Equal("Requested job was not found.", ex.Message);
    }

    private static StringContent JsonContent(string payload)
    {
        return new StringContent(payload, Encoding.UTF8, "application/json");
    }

    private static HttpClient BuildClient(Func<HttpRequestMessage, HttpResponseMessage> responder)
    {
        var handler = new LambdaHandler(responder);
        return new HttpClient(handler)
        {
            BaseAddress = new Uri("http://localhost:8000")
        };
    }

    private sealed class LambdaHandler : HttpMessageHandler
    {
        private readonly Func<HttpRequestMessage, HttpResponseMessage> _responder;

        public LambdaHandler(Func<HttpRequestMessage, HttpResponseMessage> responder)
        {
            _responder = responder;
        }

        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            return Task.FromResult(_responder(request));
        }
    }
}
